#!/usr/bin/env python3
"""
MedSync — Vetspire Intraday Usage Sync
-----------------------------------------
Runs every 5 min during business hours via GitHub Actions. Pulls dispensed
products for all active locations and upserts to Supabase dispensed_items,
enabling the "Today" view in Procurement.

Vetspire's usageReport(startDate,endDate) windowing is unreliable — it has
been confirmed to silently omit a real order item that squarely falls
inside the requested window (see reconcile_dispensed_items.py's module
docstring). Because this script previously queried s=today, e=today and
NEVER revisited a day once it passed, a single dropped poll meant that
item was gone for good — no scheduled process ever re-checked it (the only
retroactive tool, backfill_date_range.py, is workflow_dispatch-only, i.e.
a human has to notice and run it by hand). This is exactly how two real
dispenses (Lincoln Park order_item_id 4028939709, Old Orchard 4098962168)
went permanently uncaptured for over a week. So this script now queries a
rolling WIDE_LOOKBACK_DAYS window and re-upserts every item in it on every
5-minute run — upserts are idempotent by (order_item_id, location_id), so
re-touching recent days constantly is safe, and it means any single-poll
drop self-heals on the very next run instead of requiring a human to catch
it via the reconcile red X and manually backfill.

One row per real Vetspire order item, keyed by (order_item_id, location_id)
— NOT aggregated by day/product. This is the single natural key every
dispensed_items writer in this repo uses (see dispensed_items_backfill.py,
backfill_date_range.py, wheaton_usage_pull.py) specifically so that two
different scripts can never disagree on grouping and double-count the same
real event — that disagreement (day-level vs month-level aggregation) is
what caused the Aug 2026 double-count incident. Never reintroduce
aggregation here; if you need per-day/per-month totals, compute them with
a SQL view over these rows, not by pre-aggregating at write time.

Auth: VETSPIRE_API_TOKEN env var (GitHub Actions secret — raw API token,
      no Bearer prefix needed; confirmed same pattern as vetspire_daily_sync.py)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

PRACTICE_TZ = ZoneInfo("America/Chicago")  # all 4 Scout locations are Chicago-area

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s between attempts


def _urlopen_with_retry(req, timeout):
    """Retries transient failures (5xx, connection resets, timeouts) with backoff.
    4xx errors are raised immediately -- retrying a bad request won't help.
    Without this, a single Supabase HTTP 500 or a dropped TLS connection killed
    the whole run outright instead of costing a few seconds."""
    last_err = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"    transient error ({last_err}) — retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            time.sleep(wait)
    raise last_err

WIDE_LOOKBACK_DAYS = 7  # rolling window re-upserted every run; small enough to keep a
                        # 5-minute-cadence query cheap, wide enough to self-heal any
                        # single-poll drop well before a human would notice via reconcile

# ── Config ─────────────────────────────────────────────────────────────────
VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = [
    {"id": "23083", "name": "Lincoln Park"},
    {"id": "27390", "name": "Old Orchard"},
    {"id": "24356", "name": "West Loop"},
    {"id": "28253", "name": "Wheaton"},
]

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            productId
            product { id name sku unitCost }
            quantity
            quantityRemaining
            unitPrice
            subtotalCents
            totalBeforeTaxCents
            returned
            refunded
            updatedAt
        }
    }
}
"""

# ── Vetspire ────────────────────────────────────────────────────────────────
def gql(token, query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": token,
            "Origin":        VETSPIRE_ORIGIN,
        }
    )
    body, _ = _urlopen_with_retry(req, timeout=30)
    return json.loads(body)

# ── Supabase ────────────────────────────────────────────────────────────────
def supa_upsert(records):
    if not records:
        return 0
    conflict = "order_item_id,location_id"
    payload = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + f"/rest/v1/dispensed_items?on_conflict={conflict}",
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "resolution=merge-duplicates,return=minimal",
        }
    )
    req.get_method = lambda: "POST"
    try:
        _, status = _urlopen_with_retry(req, timeout=30)
        return status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Supabase error {e.code}: {body[:300]}")
        return e.code


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: VETSPIRE_API_TOKEN env var not set.")
        sys.exit(1)

    # date.today() reads the GitHub Actions runner's UTC clock — during the
    # Central-time evening (~6pm-midnight CDT/CST), that's already tomorrow's
    # UTC date while Vetspire still buckets usageReport by the local practice
    # day. Querying the wrong day drops that evening's dispensing entirely
    # (confirmed: diagnosed a 78-vs-71 gap for Catalyst Chem 17 @ Wheaton, all
    # 7 missing units sitting in the 7pm-CDT hour — see diagnose_dispensed_gap.py).
    # The rolling wide-range query below also protects against this: even if
    # one run reads the wrong day, the next run's window still covers it.
    today = datetime.now(PRACTICE_TZ).date()
    wide_start = (today - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()
    today_iso = today.isoformat()
    now_utc = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Intraday Usage Sync — rolling {wide_start} → {today_iso} (run at {now_utc} UTC) ===")

    total = 0
    errors = 0

    for loc in LOCATIONS:
        print(f"\n  [{loc['name']}] pulling usageReport...")
        try:
            r = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": wide_start, "e": today_iso})
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            continue

        if "errors" in r:
            print(f"  API error: {r['errors'][0]['message'][:200]}")
            errors += 1
            continue

        usage_raw = r.get("data", {}).get("usageReport")
        # usageReport may return a JSON string (like salesReport) — parse if so
        if isinstance(usage_raw, str):
            try:
                usage_raw = json.loads(usage_raw)
            except Exception:
                pass
        if isinstance(usage_raw, list):
            order_items = usage_raw
        elif isinstance(usage_raw, dict):
            order_items = usage_raw.get("orderItems", [])
        else:
            order_items = []
        order_items = list({str(it.get("id")): it for it in order_items}.values())  # dedupe by id
        print(f"  {len(order_items)} order items in the {WIDE_LOOKBACK_DAYS}-day rolling window")

        # One row per real order item — no aggregation. order_item_id is the
        # sole natural key (see module docstring for why aggregation is banned
        # here).
        records = []
        skipped = 0
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            oid  = item.get("id")
            if not pid or not oid:
                skipped += 1
                continue  # skip true services with no product ID, or malformed rows with no item id

            try:
                unit_price = float(item.get("unitPrice") or 0)
            except (ValueError, TypeError):
                unit_price = 0.0

            unit_cost = prod.get("unitCost")
            updated_at = item.get("updatedAt")
            dispensed_at = updated_at if updated_at else now_utc
            if dispensed_at and "T" in dispensed_at and not dispensed_at.endswith("Z") and "+" not in dispensed_at[10:]:
                dispensed_at += "Z"  # Vetspire returns naive datetimes — treat as UTC

            records.append({
                "order_item_id":          str(oid),
                "vetspire_product_id":    str(pid),
                "product_name":           prod.get("name"),
                "sku":                    prod.get("sku"),
                "quantity":               float(item.get("quantity") or 0),
                "quantity_remaining":     float(item.get("quantityRemaining") or 0),
                "unit_price":             unit_price,
                "unit_cost":              float(unit_cost) if unit_cost is not None else None,
                "subtotal_cents":         int(item.get("subtotalCents") or 0),
                "total_before_tax_cents": int(item.get("totalBeforeTaxCents") or 0),
                "returned":               bool(item.get("returned", False)),
                "refunded":               bool(item.get("refunded", False)),
                "dispensed_at":           dispensed_at,
                "location_id":            loc["id"],
                "location_name":          loc["name"],
                "pulled_at":              now_utc,
            })

        if records:
            location_ok = True
            for batch in chunks(records, 500):
                status = supa_upsert(batch)
                if not str(status).startswith("2"):
                    print(f"  Upsert FAILED for a batch of {len(batch)} → HTTP {status}")
                    location_ok = False
                    errors += 1
                    continue
                total += len(batch)
            suffix = "" if location_ok else " — WITH FAILURES"
            print(f"  Upserted {len(records)} records ({skipped} skipped, no product/item id){suffix}")
        else:
            print(f"  No physical inventory items in window ({skipped} skipped).")

    print(f"\n=== Done: {total} records upserted, {errors} location error(s) ===")
    if errors:
        sys.exit(1)  # ANY location failing means incomplete data for that location —
                      # never treat a partial run as success

if __name__ == "__main__":
    main()
