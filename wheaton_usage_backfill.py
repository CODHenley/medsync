#!/usr/bin/env python3
"""
One-time backfill — pulls the last 90 days of Wheaton usage data
from Vetspire and upserts all physical inventory items to Supabase.
Run once manually; nightly script handles daily pulls going forward.
"""

import json, urllib.request, urllib.error, os, sys, base64
from datetime import date, datetime, timezone, timedelta

TOKEN_FILE        = os.path.expanduser("~/.vetspire_token")
VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN   = "https://scoutcare.vetspire.com"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
WHEATON_ID        = "28253"
BACKFILL_DAYS     = 90  # change to 180 for 6 months

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
print(f"Token loaded: {token[:20]}...")

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

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def supa_upsert(records):
    if not records:
        return 201
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items?on_conflict=vetspire_product_id,dispensed_at,location_id",
        data=body,
        headers={
            "Content-Type": "application/json",
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
    )
    req.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code}: {e.read().decode()[:200]}")
        return e.code

# Pull in monthly chunks to avoid large responses
today      = date.today()
start_date = today - timedelta(days=BACKFILL_DAYS)

print(f"\nBackfilling {BACKFILL_DAYS} days: {start_date} → {today}")
print("Pulling in monthly chunks...\n")

total_records = 0
total_skipped = 0
seen_products = set()

# Chunk by month
cursor = start_date
while cursor <= today:
    chunk_end = min(date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1) - timedelta(days=1), today)
    s = cursor.isoformat()
    e = chunk_end.isoformat()
    print(f"  Pulling {s} → {e}...")

    try:
        r = gql(USAGE_QUERY, {"lids": [WHEATON_ID], "s": s, "e": e})
    except Exception as ex:
        print(f"  ERROR: {ex}")
        cursor = chunk_end + timedelta(days=1)
        continue

    if "errors" in r:
        print(f"  API error: {r['errors'][0]['message'][:150]}")
        cursor = chunk_end + timedelta(days=1)
        continue

    order_items = r.get("data", {}).get("usageReport", {}).get("orderItems", [])
    print(f"  {len(order_items)} items returned")

    records = []
    for item in order_items:
        prod = item.get("product") or {}
        pid  = item.get("productId") or prod.get("id")
        if not pid:
            continue

        unit_cost = prod.get("unitCost")
        sku       = prod.get("sku")

        # Skip services — only physical inventory
        if not sku and unit_cost is None:
            total_skipped += 1
            continue

        updated_at = item.get("updatedAt") or datetime.now(timezone.utc).isoformat()
        if "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        try:
            unit_price = float(item.get("unitPrice") or 0)
        except (ValueError, TypeError):
            unit_price = 0.0

        seen_products.add(prod.get("name", pid))
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
            "location_id":            WHEATON_ID,
            "location_name":          "Wheaton",
            "pulled_at":              datetime.now(timezone.utc).isoformat(),
        })

    if records:
        status = supa_upsert(records)
        if str(status).startswith("2"):
            print(f"  ✓ Upserted {len(records)} records")
            total_records += len(records)
        else:
            print(f"  ✗ Failed (status {status})")

    cursor = chunk_end + timedelta(days=1)

print(f"\n{'='*50}")
print(f"Backfill complete!")
print(f"  Records upserted : {total_records}")
print(f"  Services skipped : {total_skipped}")
print(f"  Unique products  : {len(seen_products)}")
print(f"\nProducts tracked:")
for name in sorted(seen_products):
    print(f"  · {name}")
