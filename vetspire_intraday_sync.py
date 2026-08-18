#!/usr/bin/env python3
"""
MedSync — Vetspire Intraday Usage Sync
-----------------------------------------
Runs every 5 min during business hours via GitHub Actions. Pulls today's
dispensed products for all active locations and upserts to Supabase
dispensed_items, enabling the "Today" view in Procurement.

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
import urllib.request
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PRACTICE_TZ = ZoneInfo("America/Chicago")  # all 4 Scout locations are Chicago-area

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
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

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
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Supabase error {e.code}: {body[:300]}")
        return e.code

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: VETSPIRE_API_TOKEN env var not set.")
        sys.exit(1)

    # date.today() reads the GitHub Actions runner's UTC clock — during the
    # Central-time evening (~6pm-midnight CDT/CST), that's already tomorrow's
    # UTC date while Vetspire still buckets usageReport by the local practice
    # day. Querying the wrong day drops that evening's dispensing entirely,
    # since this script never revisits a stale day (confirmed: diagnosed a
    # 78-vs-71 gap for Catalyst Chem 17 @ Wheaton, all 7 missing units sitting
    # in the 7pm-CDT hour — see diagnose_dispensed_gap.py).
    today = datetime.now(PRACTICE_TZ).date().isoformat()
    now_utc = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Intraday Usage Sync — {today} (local practice date; run at {now_utc} UTC) ===")

    total = 0
    errors = 0

    for loc in LOCATIONS:
        print(f"\n  [{loc['name']}] pulling usageReport...")
        try:
            r = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": today, "e": today})
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
        print(f"  {len(order_items)} order items")

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
            status = supa_upsert(records)
            if not str(status).startswith("2"):
                print(f"  Upsert FAILED → HTTP {status}")
                errors += 1
                continue
            print(f"  Upserted {len(records)} records ({skipped} skipped, no product/item id) → HTTP {status}")
            total += len(records)
        else:
            print(f"  No physical inventory items today ({skipped} skipped).")

    print(f"\n=== Done: {total} records upserted, {errors} location error(s) ===")
    if errors:
        sys.exit(1)  # ANY location failing means incomplete data for that location —
                      # never treat a partial run as success

if __name__ == "__main__":
    main()
