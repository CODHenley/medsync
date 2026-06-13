#!/usr/bin/env python3
"""
Wheaton Inventory Sync — computes current on-hand per product by summing
all Vetspire inventoryAdjustments, then upserts into inventory_snapshots.

How it works:
  Vetspire tracks every stock change (receiving, cycle count correction,
  wastage, dispense) as an InventoryAdjustment with a quantityChange.
  Summing all quantityChanges per product = current on-hand. This is
  exactly what Vetspire's own UI displays.

Runs every 4 hours:
  30 */4 * * * /usr/bin/python3 ~/Desktop/medsync_deploy/wheaton_inventory_sync.py >> ~/Desktop/medsync_deploy/inventory_sync.log 2>&1

Token refresh:
  python3 -c "open('/Users/meganhenley/.vetspire_token','w').write('TOKEN')"
"""

import json, urllib.request, urllib.error, os, sys, base64
from datetime import date, datetime, timezone

TOKEN_FILE        = os.path.expanduser("~/.vetspire_token")
VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN   = "https://scoutcare.vetspire.com"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
WHEATON_ID        = "28253"
WHEATON_NAME      = "Wheaton"

# ── Token ─────────────────────────────────────────────────────────────────────
token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
try:
    payload = token.split(".")[1] + "=="
    data    = json.loads(base64.urlsafe_b64decode(payload))
    exp     = data.get("exp", 0)
    now     = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print("TOKEN EXPIRED — refresh it first"); sys.exit(1)
    print(f"Token valid for {(exp-now)/3600:.1f}h")
except Exception as e:
    print(f"Token decode warning: {e}")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req  = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin":        VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

# ── Pull all inventory adjustments for Wheaton ────────────────────────────────
QUERY = """
query($lid: ID!) {
    inventoryAdjustments(locationId: $lid) {
        id
        quantityChange
        insertedAt
        product { id name sku unitCost }
    }
}
"""

print(f"\n=== Wheaton Inventory Sync — {date.today()} ===")
print(f"  Pulling inventoryAdjustments for Wheaton ({WHEATON_ID})...")

try:
    result = gql(QUERY, {"lid": WHEATON_ID})
except Exception as e:
    print(f"  ERROR: {e}"); sys.exit(1)

if "errors" in result:
    print(f"  API error: {result['errors'][0]['message']}")
    sys.exit(1)

adjustments = result.get("data", {}).get("inventoryAdjustments", [])
print(f"  {len(adjustments)} adjustment records returned")

if not adjustments:
    print("  No data — exiting"); sys.exit(0)

# ── Sum quantityChange per product = current on-hand ─────────────────────────
on_hand   = {}   # product_id -> running total
prod_meta = {}   # product_id -> { name, sku, unit_cost }

for adj in adjustments:
    prod = adj.get("product") or {}
    pid  = str(prod.get("id") or adj.get("id") or "")
    if not pid:
        continue

    qty = float(adj.get("quantityChange") or 0)
    on_hand[pid]   = on_hand.get(pid, 0.0) + qty
    prod_meta[pid] = {
        "name":      prod.get("name") or "",
        "sku":       prod.get("sku"),
        "unit_cost": float(prod.get("unitCost")) if prod.get("unitCost") is not None else (prod_meta[pid]["unit_cost"] if pid in prod_meta else None),
    }

print(f"  {len(on_hand)} unique products found")

# ── Build Supabase records ────────────────────────────────────────────────────
today_str = date.today().isoformat()
pulled_at = datetime.now(timezone.utc).isoformat()
records   = []
skipped   = 0

for pid, qty in on_hand.items():
    meta = prod_meta[pid]
    if not meta["name"]:
        skipped += 1
        continue
    records.append({
        "vetspire_location_id": WHEATON_ID,
        "location_name":        WHEATON_NAME,
        "vetspire_product_id":  pid,
        "product_name":         meta["name"],
        "on_hand":              round(qty, 4),
        "snapshot_date":        today_str,
        "created_at":           pulled_at,
    })

print(f"  {len(records)} records to upsert  ({skipped} skipped — no name)")

# ── Upsert to Supabase ────────────────────────────────────────────────────────
def supa_upsert(batch):
    body = json.dumps(batch).encode()
    req  = urllib.request.Request(
        SUPA_URL + "/rest/v1/inventory_snapshots?on_conflict=vetspire_product_id,vetspire_location_id",
        data=body,
        headers={
            "Content-Type": "application/json",
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
        print(f"  Supabase error {e.code}: {e.read().decode()[:200]}")
        return e.code

CHUNK    = 100
total_ok = 0
for i in range(0, len(records), CHUNK):
    batch  = records[i:i+CHUNK]
    status = supa_upsert(batch)
    if str(status).startswith("2"):
        total_ok += len(batch)
    else:
        print(f"  ✗ Chunk {i//CHUNK+1} failed (status {status})")

print(f"\n  ✓ {total_ok} inventory snapshots upserted")

# Print summary
print(f"\n  Top on-hand quantities:")
top = sorted(on_hand.items(), key=lambda x: -x[1])[:15]
for pid, qty in top:
    name = prod_meta[pid]["name"]
    print(f"    {qty:>8.1f}  {name}")

print(f"\nDone.\n")
