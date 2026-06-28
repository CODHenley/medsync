#!/usr/bin/env python3
"""
MedSync — Vetspire Intraday Usage Sync
-----------------------------------------
Runs 4x daily (7am, noon, 7pm, midnight CST) via GitHub Actions.
Pulls today's dispensed products for all active locations and upserts
to Supabase dispensed_items, enabling the "Today" view in Procurement.

Auth: VETSPIRE_API_TOKEN env var (GitHub Actions secret — raw API token,
      no Bearer prefix needed; confirmed same pattern as vetspire_daily_sync.py)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timezone

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
    payload = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items",
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

    today = date.today().isoformat()
    now_utc = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Intraday Usage Sync — {today} (run at {now_utc}) ===")

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

        order_items = r.get("data", {}).get("usageReport", {}).get("orderItems", [])
        print(f"  {len(order_items)} order items")

        records = []
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            sku  = prod.get("sku")
            if not pid or not sku:
                continue  # skip services / non-inventory items

            updated_at = item.get("updatedAt") or now_utc
            if "+" not in updated_at and "Z" not in updated_at:
                updated_at += "Z"

            try:
                unit_price = float(item.get("unitPrice") or 0)
            except (ValueError, TypeError):
                unit_price = 0.0

            unit_cost = prod.get("unitCost")

            records.append({
                "vetspire_product_id":    pid,
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
                "dispensed_at":           updated_at,
                "location_id":            loc["id"],
                "location_name":          loc["name"],
                "pulled_at":              now_utc,
            })

        if records:
            status = supa_upsert(records)
            print(f"  Upserted {len(records)} records → HTTP {status}")
            total += len(records)
        else:
            print(f"  No physical inventory items today.")

    print(f"\n=== Done: {total} records upserted, {errors} location error(s) ===")
    if errors == len(LOCATIONS):
        sys.exit(1)  # all locations failed — fail the workflow run

if __name__ == "__main__":
    main()
