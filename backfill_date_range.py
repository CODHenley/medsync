#!/usr/bin/env python3
"""
One-time backfill for a date range.

Usage:
    python3 backfill_date_range.py 2026-08-01 2026-08-05

Pulls all dispensed items from Vetspire for each day in the range and
upserts to Supabase dispensed_items, fixing gaps caused by the intraday
sync previously skipping items with no SKU (in-house/QC events).

Auth: VETSPIRE_API_TOKEN env var.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone

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

def supa_upsert(records):
    if not records:
        return 0
    payload = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items?on_conflict=vetspire_product_id,dispensed_at,location_id",
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
        print(f"  Supabase error {e.code}: {e.read().decode()[:300]}")
        return e.code

def date_range(start_str, end_str):
    start = date.fromisoformat(start_str)
    end   = date.fromisoformat(end_str)
    d = start
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)

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

    for day in date_range(start_date, end_date):
        print(f"--- {day} ---")
        for loc in LOCATIONS:
            try:
                r = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": day, "e": day})
            except Exception as e:
                print(f"  [{loc['name']}] ERROR: {e}")
                total_errors += 1
                continue

            if "errors" in r:
                print(f"  [{loc['name']}] API error: {r['errors'][0]['message'][:200]}")
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

            dispensed_at = day + "T00:00:00Z"
            agg = {}
            for item in order_items:
                prod = item.get("product") or {}
                pid  = item.get("productId") or prod.get("id")
                sku  = prod.get("sku")
                if not pid:
                    continue  # skip true services with no product ID

                try:
                    unit_price = float(item.get("unitPrice") or 0)
                except (ValueError, TypeError):
                    unit_price = 0.0

                unit_cost = prod.get("unitCost")
                key = (str(pid), dispensed_at, loc["id"])
                if key in agg:
                    e = agg[key]
                    e["quantity"]               += float(item.get("quantity") or 0)
                    e["quantity_remaining"]     += float(item.get("quantityRemaining") or 0)
                    e["subtotal_cents"]         += int(item.get("subtotalCents") or 0)
                    e["total_before_tax_cents"] += int(item.get("totalBeforeTaxCents") or 0)
                    if bool(item.get("returned", False)):
                        e["returned"] = True
                    if bool(item.get("refunded", False)):
                        e["refunded"] = True
                    if sku and not e["sku"]:
                        e["sku"] = sku
                else:
                    agg[key] = {
                        "order_item_id":          None,
                        "vetspire_product_id":    str(pid),
                        "product_name":           prod.get("name"),
                        "sku":                    sku,
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
                    }

            records = list(agg.values())
            if records:
                status = supa_upsert(records)
                print(f"  [{loc['name']}] {len(records)} products → HTTP {status}")
                total_upserted += len(records)
            else:
                print(f"  [{loc['name']}] no items")

    print(f"\n=== Done: {total_upserted} records upserted, {total_errors} error(s) ===\n")

if __name__ == "__main__":
    main()
