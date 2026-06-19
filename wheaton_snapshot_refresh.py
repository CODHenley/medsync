#!/usr/bin/env python3
"""
Wheaton Snapshot Refresh
Pulls current on-hand from Vetspire using products+inventoryLevels
and upserts into inventory_snapshots. Run this whenever you need
to refresh Wheaton's product data in MedSync.

Usage:
    python3 ~/Desktop/medsync_deploy/wheaton_snapshot_refresh.py
"""

import json, urllib.request, urllib.error, os, sys
from datetime import date, datetime, timezone

VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN   = "https://scoutcare.vetspire.com"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
WHEATON_ID        = "28253"
WHEATON_NAME      = "Wheaton"
TOKEN_FILE        = os.path.join(os.path.dirname(__file__), "vetspire_token.txt")

token = open(TOKEN_FILE).read().strip()
print(f"Using API token from vetspire_token.txt")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req  = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "Origin":        VETSPIRE_ORIGIN,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        sys.exit(1)

QUERY = """
query getStock($locationId: ID!, $limit: Int, $offset: Int) {
    products(onlyTrackInventory: true, onlyEnabledAt: $locationId, limit: $limit, offset: $offset) {
        id
        name
        sku
        unitCost
        inventoryLevels(locationId: $locationId) {
            stock
        }
    }
}
"""

print(f"\n=== Wheaton Snapshot Refresh — {date.today()} ===")
print(f"  Pulling products for Wheaton ({WHEATON_ID})...")

all_products = []
offset = 0
limit  = 500
while True:
    result = gql(QUERY, {"locationId": WHEATON_ID, "limit": limit, "offset": offset})
    if "errors" in result:
        print(f"  API error: {result['errors'][0]['message']}")
        sys.exit(1)
    page = result.get("data", {}).get("products", [])
    if not page:
        break
    all_products.extend(page)
    if len(page) < limit:
        break
    offset += limit

print(f"  {len(all_products)} products found")

today_str = date.today().isoformat()
records   = []
for p in all_products:
    name   = (p.get("name") or "").strip()
    pid    = str(p.get("id") or "")
    levels = p.get("inventoryLevels") or []
    stock  = sum(float(l.get("stock") or 0) for l in levels)
    cost   = float(p.get("unitCost") or 0) if p.get("unitCost") is not None else None
    if not name or not pid:
        continue
    records.append({
        "vetspire_location_id": WHEATON_ID,
        "location_name":        WHEATON_NAME,
        "vetspire_product_id":  pid,
        "product_name":         name,
        "on_hand":              round(stock, 4),
        "snapshot_date":        today_str,
        "unit_cost":            cost,
    })

# Deduplicate by product ID (Vetspire occasionally returns the same product twice)
seen_pids = {}
for r in records:
    seen_pids[r["vetspire_product_id"]] = r
records = list(seen_pids.values())
print(f"  {len(records)} records to insert (after dedup)")

# Fetch existing product IDs already stored for Wheaton today
existing_url = SUPA_URL + f"/rest/v1/inventory_snapshots?select=vetspire_product_id&vetspire_location_id=eq.{WHEATON_ID}&snapshot_date=eq.{today_str}&limit=2000"
existing_req = urllib.request.Request(existing_url, headers={
    "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"
})
with urllib.request.urlopen(existing_req, timeout=30) as r:
    existing = {row["vetspire_product_id"] for row in json.loads(r.read())}
print(f"  {len(existing)} products already in DB for today")

to_insert = [r for r in records if r["vetspire_product_id"] not in existing]
to_update = [r for r in records if r["vetspire_product_id"] in existing]

# Insert new records
BATCH = 200
inserted = 0
for i in range(0, len(to_insert), BATCH):
    batch = to_insert[i:i+BATCH]
    body  = json.dumps(batch).encode()
    req   = urllib.request.Request(
        SUPA_URL + "/rest/v1/inventory_snapshots",
        data=body,
        headers={
            "Content-Type": "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "return=minimal",
        }
    )
    req.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            inserted += len(batch)
    except urllib.error.HTTPError as e:
        print(f"  Insert error: {e.read().decode()[:300]}")
        sys.exit(1)

# Update existing records one by one (on_hand may have changed)
updated = 0
for rec in to_update:
    pid  = rec["vetspire_product_id"]
    body = json.dumps({"on_hand": rec["on_hand"], "unit_cost": rec["unit_cost"]}).encode()
    req  = urllib.request.Request(
        SUPA_URL + f"/rest/v1/inventory_snapshots?vetspire_location_id=eq.{WHEATON_ID}&vetspire_product_id=eq.{pid}&snapshot_date=eq.{today_str}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "return=minimal",
        }
    )
    req.get_method = lambda: "PATCH"
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            updated += 1
    except urllib.error.HTTPError as e:
        print(f"  Update error for {pid}: {e.read().decode()[:200]}")

print(f"  Inserted {inserted} new, updated {updated} existing ✓")

print(f"\nDone — {len(records)} Wheaton products synced to MedSync.")
