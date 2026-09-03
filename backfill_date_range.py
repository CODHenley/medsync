#!/usr/bin/env python3
"""
One-time backfill for a date range.

Usage:
    python3 backfill_date_range.py 2026-08-01 2026-08-05

Pulls dispensed items from Vetspire for the given range (one query per
location — no day-by-day loop) and upserts to Supabase dispensed_items.

One row per real Vetspire order item, keyed by (order_item_id, location_id)
— NOT aggregated by day/product. This is the single natural key every
dispensed_items writer in this repo uses (see vetspire_intraday_sync.py,
dispensed_items_backfill.py, wheaton_usage_pull.py) specifically so that two
different scripts can never disagree on grouping and double-count the same
real event — that disagreement (day-level vs month-level aggregation) is
what caused the Aug 2026 double-count incident. Never reintroduce
aggregation here; if you need per-day/per-month totals, compute them with a
SQL view over these rows, not by pre-aggregating at write time. Re-running
this script for the same range is always safe/idempotent — the same order
item always maps to the same row.

Vetspire's usageReport(startDate,endDate) windowing is unreliable — it has
been confirmed to silently omit a real order item that squarely falls
inside the requested window (see reconcile_dispensed_items.py's module
docstring). This bit this exact script: a manual dispatch for 2026-08-06 to
2026-08-09, run specifically to capture a known-missing Lincoln Park item
(order_item_id 4028939709), completed with 0 errors and STILL didn't
capture it — re-verified missing immediately after. So this script now
queries a wide, padded range and filters by updatedAt on our side instead
of trusting Vetspire's own date filter, matching the fix already applied
to reconcile_dispensed_items.py and vetspire_intraday_sync.py.

Auth: VETSPIRE_API_TOKEN env var.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s between attempts


def _urlopen_with_retry(req, timeout):
    """Retries transient failures (5xx, connection resets, timeouts) with backoff.
    4xx errors are raised immediately -- retrying a bad request won't help.
    This script previously had none of this (unlike every scheduled script in
    this repo) since workflow_dispatch-only jobs were missed by the "cron:"
    grep used to find which scripts needed it -- a dispatch that stalled on a
    single slow/dropped Vetspire or Supabase call had no way to recover short
    of a human noticing and re-dispatching by hand."""
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

WIDE_LOOKBACK_DAYS = 180

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3"
            "Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
            ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s")

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
            product { id name sku unitCost productCategories { id name } }
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
    body, _ = _urlopen_with_retry(req, timeout=60)
    return json.loads(body)


def supa_upsert(records):
    if not records:
        return 0
    payload = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items?on_conflict=order_item_id,location_id",
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


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: VETSPIRE_API_TOKEN env var not set.")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python3 backfill_date_range.py <start> <end>  (e.g. 2026-08-01 2026-08-05)")
        sys.exit(1)

    start_date = sys.argv[1]
    end_date   = sys.argv[2]
    now_utc    = datetime.now(timezone.utc).isoformat()

    print(f"\n=== Backfill {start_date} → {end_date} ===\n")

    total_upserted = 0
    total_errors   = 0

    wide_start = (datetime.strptime(start_date, "%Y-%m-%d").date() - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()

    for loc in LOCATIONS:
        print(f"--- {loc['name']} ---")
        try:
            r = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": wide_start, "e": end_date})
        except Exception as e:
            print(f"  ERROR: {e}")
            total_errors += 1
            continue

        if "errors" in r:
            print(f"  API error: {r['errors'][0]['message'][:200]}")
            total_errors += 1
            continue

        usage_raw = r.get("data", {}).get("usageReport")
        if isinstance(usage_raw, str):
            try:
                usage_raw = json.loads(usage_raw)
            except Exception:
                pass
        order_items = (usage_raw.get("orderItems", []) if isinstance(usage_raw, dict)
                       else usage_raw if isinstance(usage_raw, list) else [])
        order_items = list({str(it.get("id")): it for it in order_items}.values())  # dedupe by id
        order_items = [it for it in order_items if start_date <= (it.get("updatedAt") or "")[:10] <= end_date]
        print(f"  {len(order_items)} order items in {start_date}..{end_date} (via wide-range query)")

        records = []
        skipped = 0
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            oid  = item.get("id")
            if not pid or not oid:
                skipped += 1
                continue

            try:
                unit_price = float(item.get("unitPrice") or 0)
            except (ValueError, TypeError):
                unit_price = 0.0

            unit_cost = prod.get("unitCost")
            updated_at = item.get("updatedAt")
            dispensed_at = updated_at if updated_at else now_utc
            if dispensed_at and "T" in dispensed_at and not dispensed_at.endswith("Z") and "+" not in dispensed_at[10:]:
                dispensed_at += "Z"  # Vetspire returns naive datetimes — treat as UTC

            # productCategories is a list -- confirmed live (scoutsync_service_
            # category_probe.py) that a product carries 0 or 1 in practice,
            # never more; take the first if one is ever present. None means
            # Vetspire itself has no category for this product.
            categories = prod.get("productCategories") or []
            try:
                category_id = int(categories[0]["id"]) if categories else None
            except (KeyError, TypeError, ValueError):
                category_id = None

            records.append({
                "order_item_id":          str(oid),
                "vetspire_product_id":    str(pid),
                "product_name":           prod.get("name"),
                "sku":                    prod.get("sku"),
                "quantity":               float(item.get("quantity") or 0),
                "quantity_remaining":     float(item.get("quantityRemaining") or 0),
                "unit_price":             unit_price,
                "unit_cost":              float(unit_cost) if unit_cost is not None else None,
                "product_category_id":    category_id,
                "subtotal_cents":         int(item.get("subtotalCents") or 0),
                "total_before_tax_cents": int(item.get("totalBeforeTaxCents") or 0),
                "returned":               bool(item.get("returned", False)),
                "refunded":               bool(item.get("refunded", False)),
                "dispensed_at":           dispensed_at,
                "location_id":            loc["id"],
                "location_name":          loc["name"],
                "pulled_at":              now_utc,
            })

        if not records:
            print(f"  no items ({skipped} skipped)")
            continue

        location_ok = True
        for batch in chunks(records, 500):
            status = supa_upsert(batch)
            if not str(status).startswith("2"):
                print(f"  upsert FAILED for a batch of {len(batch)} → HTTP {status}")
                location_ok = False
                total_errors += 1
                continue
            total_upserted += len(batch)
        suffix = "" if location_ok else " — WITH FAILURES"
        print(f"  upserted {len(records)} records ({skipped} skipped, no product/item id){suffix}")

    print(f"\n=== Done: {total_upserted} records upserted, {total_errors} error(s) ===\n")
    if total_errors:
        sys.exit(1)  # any failure means the range is incompletely backfilled — never report success


if __name__ == "__main__":
    main()
