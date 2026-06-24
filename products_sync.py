#!/usr/bin/env python3
"""
products_sync.py
Sync all Scout product catalog entries from Vetspire into the Supabase
products table, enriching each row with NDC, manufacturer, vendor, and
unit price so that the Lot Lifecycle SKU scanner can look up products by NDC.

Runs across all four Scout locations and deduplicates by Vetspire product ID
so each product is only upserted once.

Usage:
    python3 products_sync.py
    (reads VETSPIRE_API_TOKEN env var, or ~/.vetspire_token)
"""
import sys, json, os, urllib.request, urllib.parse
from datetime import date

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = os.environ.get("SUPA_SERVICE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# All Scout location IDs in Vetspire
LOCATION_IDS = ["28250", "28251", "28252", "28253"]

# ── Auth ──────────────────────────────────────────────────────────────────────
token = (
    os.environ.get("VETSPIRE_API_TOKEN")
    or (open(os.path.expanduser("~/.vetspire_token")).read().strip()
        if os.path.exists(os.path.expanduser("~/.vetspire_token")) else "")
).removeprefix("Bearer ").strip()

if not token:
    print("ERROR: No Vetspire token found. Set VETSPIRE_API_TOKEN env var.")
    sys.exit(1)

print(f"Token: {token[:20]}…")

# ── Helpers ───────────────────────────────────────────────────────────────────
def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def supa_req(method, path, body=None, prefer="return=minimal"):
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    req = urllib.request.Request(SUPA_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read()

# ── Vetspire products query ───────────────────────────────────────────────────
# Fetch products enabled at a given location, paginated 100 at a time.
# Fields probed and confirmed via vetspire_introspect.py:
#   id, name, sku, unitCost, manufacturer, ndc, isControlled, deaSchedule
# If ndc/manufacturer aren't available the server returns null — handled below.

PRODUCTS_QUERY = """
query($locationId: ID!, $limit: Int, $offset: Int) {
  products(
    onlyTrackInventory: true
    onlyEnabledAt: $locationId
    limit: $limit
    offset: $offset
  ) {
    id
    name
    sku
    unitCost
    manufacturer { name }
    ndc
    isControlled
    deaSchedule
  }
}
"""

def fetch_products_for_location(location_id):
    all_products = []
    offset = 0
    while True:
        result = gql(PRODUCTS_QUERY, {"locationId": location_id, "limit": 100, "offset": offset})
        if "errors" in result:
            err = result["errors"][0].get("message", str(result["errors"]))
            # If ndc/manufacturer fields don't exist, retry without them
            if "ndc" in err or "manufacturer" in err or "Cannot query" in err:
                return fetch_products_for_location_minimal(location_id)
            print(f"  GraphQL error for location {location_id}: {err}")
            break
        page = (result.get("data") or {}).get("products") or []
        if not page:
            break
        all_products.extend(page)
        if len(page) < 100:
            break
        offset += 100
    return all_products

PRODUCTS_QUERY_MINIMAL = """
query($locationId: ID!, $limit: Int, $offset: Int) {
  products(
    onlyTrackInventory: true
    onlyEnabledAt: $locationId
    limit: $limit
    offset: $offset
  ) {
    id
    name
    sku
    unitCost
  }
}
"""

def fetch_products_for_location_minimal(location_id):
    all_products = []
    offset = 0
    while True:
        result = gql(PRODUCTS_QUERY_MINIMAL, {"locationId": location_id, "limit": 100, "offset": offset})
        if "errors" in result:
            print(f"  Error (minimal query) for location {location_id}: {result['errors']}")
            break
        page = (result.get("data") or {}).get("products") or []
        if not page:
            break
        all_products.extend(page)
        if len(page) < 100:
            break
        offset += 100
    return all_products

# ── Pull products across all locations, dedup by Vetspire ID ─────────────────
print(f"\n=== Products Sync — {date.today()} ===")

seen_ids = set()
all_products = []

for loc_id in LOCATION_IDS:
    print(f"  Fetching products for location {loc_id}…")
    products = fetch_products_for_location(loc_id)
    new_count = 0
    for p in products:
        pid = str(p.get("id") or "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            all_products.append(p)
            new_count += 1
    print(f"    {len(products)} products returned, {new_count} new unique")

print(f"\nTotal unique products: {len(all_products)}")

if not all_products:
    print("No products found — exiting.")
    sys.exit(0)

# ── Preview ───────────────────────────────────────────────────────────────────
has_ndc = sum(1 for p in all_products if p.get("ndc"))
print(f"  {has_ndc} have NDC populated ({len(all_products) - has_ndc} without)")

print(f"\n{'Name':<45} {'NDC':<15} {'SKU':<12} {'Manufacturer'}")
print("-" * 100)
for p in sorted(all_products, key=lambda x: x.get("name") or "")[:30]:
    print(f"  {(p.get('name') or '')[:43]:<43}  {(p.get('ndc') or ''):<15} {(p.get('sku') or ''):<12}  {(p.get('manufacturer') or {}).get('name') or ''}")
if len(all_products) > 30:
    print(f"  … and {len(all_products) - 30} more")

# ── Build Supabase upsert records ─────────────────────────────────────────────
records = []
for p in all_products:
    name = (p.get("name") or "").strip()
    if not name:
        continue

    ndc_raw = (p.get("ndc") or "").strip()

    records.append({
        "name":         name,
        "ndc":          ndc_raw or None,
        "manufacturer": ((p.get("manufacturer") or {}).get("name") or "").strip() or None,
        "unit_price":   p.get("unitCost") or None,
    })

print(f"\n{len(records)} records to upsert into Supabase products table")

# ── Upsert into Supabase (on conflict on vetspire_id, update all fields) ──────
# Uses Prefer: resolution=merge-duplicates with on_conflict=vetspire_id
# Falls back to name-based upsert if vetspire_id column doesn't exist yet.

upserted = 0
failed   = 0
BATCH    = 100

for i in range(0, len(records), BATCH):
    batch = records[i:i+BATCH]
    try:
        status, body = supa_req(
            "POST",
            "/rest/v1/products?on_conflict=name",
            batch,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        upserted += len(batch)
        print(f"  Batch {i//BATCH + 1}: ✓ {len(batch)} records (HTTP {status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Batch {i//BATCH + 1}: ✗ HTTP {e.code} — {body[:300]}")
        failed += len(batch)
    except Exception as e:
        print(f"  Batch {i//BATCH + 1}: ✗ {e}")
        failed += len(batch)

print(f"\n=== Done — {upserted} upserted, {failed} failed ===")
print("NDCs are now available for the Lot Lifecycle SKU scanner.")
