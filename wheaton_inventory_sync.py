#!/usr/bin/env python3
"""
Wheaton Inventory Sync — pulls current on-hand quantities from Vetspire
and upserts into Supabase inventory_snapshots table.

Runs every 4 hours alongside wheaton_usage_pull.py.
Cron: 30 */4 * * * /usr/bin/python3 ~/Desktop/medsync_deploy/wheaton_inventory_sync.py >> ~/Desktop/medsync_deploy/inventory_sync.log 2>&1

To refresh token:
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
    data = json.loads(base64.urlsafe_b64decode(payload))
    exp  = data.get("exp", 0)
    now  = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print("TOKEN EXPIRED — refresh it first"); sys.exit(1)
    print(f"Token valid for {(exp-now)/3600:.1f}h")
except Exception as e:
    print(f"Token decode warning: {e}")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# ── Try multiple Vetspire query shapes ────────────────────────────────────────
# Different Vetspire instances expose inventory differently.
# We try each until one returns real data.

QUERIES = [
    ("inventoryItems", """
        query($lid: ID!) {
            inventoryItems(locationId: $lid) {
                id name sku onHand reorderPoint minimum maximum unitCost
            }
        }
    """, lambda r: r.get("data",{}).get("inventoryItems"), {"lid": WHEATON_ID}),

    ("products_onHand", """
        query($lid: ID!) {
            products(locationId: $lid) {
                id name sku onHand unitCost reorderPoint minimum maximum
            }
        }
    """, lambda r: r.get("data",{}).get("products"), {"lid": WHEATON_ID}),

    ("inventoryReport", """
        query($lids: [ID!]) {
            inventoryReport(locationIds: $lids) {
                productId productName sku onHand minimum maximum unitCost
            }
        }
    """, lambda r: r.get("data",{}).get("inventoryReport"), {"lids": [WHEATON_ID]}),

    ("stockLevels", """
        query($lids: [ID!]) {
            stockLevels(locationIds: $lids) {
                productId productName quantity reorderPoint
            }
        }
    """, lambda r: r.get("data",{}).get("stockLevels"), {"lids": [WHEATON_ID]}),

    ("inventory", """
        query($lid: ID!) {
            inventory(locationId: $lid) {
                productId productName onHand minimum maximum
            }
        }
    """, lambda r: r.get("data",{}).get("inventory"), {"lid": WHEATON_ID}),
]

print(f"\n=== Wheaton Inventory Sync — {date.today()} ===")

items = None
used_query = None
for (label, query, extractor, variables) in QUERIES:
    print(f"  Trying {label}...", end=" ")
    try:
        result = gql(query, variables)
        if "errors" in result:
            print(f"✗ ({result['errors'][0]['message'][:60]})")
            continue
        data = extractor(result)
        if data and len(data) > 0:
            print(f"✓ {len(data)} items")
            items = data
            used_query = label
            break
        else:
            print("✗ (no data)")
    except Exception as e:
        print(f"✗ ({e})")

if not items:
    print("\nERROR: No Vetspire inventory query succeeded.")
    print("Run vetspire_inventory_probe.py to debug, then update QUERIES above.")
    sys.exit(1)

print(f"\nUsing query: {used_query} — {len(items)} products")

# ── Normalise field names across query shapes ─────────────────────────────────
def normalise(item):
    """Map different field names to a standard shape."""
    return {
        "vetspire_product_id": str(item.get("id") or item.get("productId") or ""),
        "product_name":        item.get("name") or item.get("productName") or "",
        "sku":                 item.get("sku"),
        "on_hand":             float(item.get("onHand") or item.get("quantity") or 0),
        "reorder_point":       float(item.get("reorderPoint")) if item.get("reorderPoint") is not None else None,
        "minimum":             float(item.get("minimum")) if item.get("minimum") is not None else None,
        "maximum":             float(item.get("maximum")) if item.get("maximum") is not None else None,
        "unit_cost":           float(item.get("unitCost")) if item.get("unitCost") is not None else None,
    }

# ── Filter & build records ────────────────────────────────────────────────────
today_str    = date.today().isoformat()
pulled_at    = datetime.now(timezone.utc).isoformat()
records      = []
skipped      = 0

for raw in items:
    n = normalise(raw)
    if not n["product_name"]:
        skipped += 1
        continue
    records.append({
        "vetspire_location_id": WHEATON_ID,
        "location_name":        WHEATON_NAME,
        "vetspire_product_id":  n["vetspire_product_id"],
        "product_name":         n["product_name"],
        "on_hand":              n["on_hand"],
        "snapshot_date":        today_str,
        "created_at":           pulled_at,
    })

print(f"  {len(records)} records to upsert, {skipped} skipped (no name)")

# ── Upsert to Supabase ────────────────────────────────────────────────────────
def supa_upsert(batch):
    body = json.dumps(batch).encode()
    req  = urllib.request.Request(
        SUPA_URL + "/rest/v1/inventory_snapshots",
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

# Upsert in chunks of 100
CHUNK = 100
total_ok = 0
for i in range(0, len(records), CHUNK):
    batch  = records[i:i+CHUNK]
    status = supa_upsert(batch)
    if str(status).startswith("2"):
        total_ok += len(batch)
    else:
        print(f"  ✗ Chunk {i//CHUNK+1} failed (status {status})")

print(f"\n  ✓ Upserted {total_ok} inventory snapshots")
print(f"\nDone.\n")
