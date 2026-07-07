#!/usr/bin/env python3
"""
products_sync.py
Sync the Scout product catalog from Vetspire into Supabase, with full
per-location enabled/disabled tracking.

For each Scout location:
  1. Pulls every product enabled at that location (onlyTrackInventory=true,
     onlyEnabledAt=<locationId>) from Vetspire.
  2. Upserts each product into the products table (keyed on vetspire_product_id).
  3. Upserts (product_id, location_id, enabled=true) into product_locations.
  4. After all locations sync: any product_locations row whose location_id was
     in scope but whose vetspire_product_id was NOT seen in this run is flipped
     to enabled=false — mirroring deactivations in Vetspire automatically.

Runs daily at 7:30am CT via GitHub Actions (products_sync.yml).
Usage:
    python3 products_sync.py
    (reads VETSPIRE_API_TOKEN env var, or ~/.vetspire_token)
"""
import sys, json, os, urllib.request, urllib.parse
from datetime import date, timezone, datetime

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

def supa_get(path):
    headers = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(SUPA_URL + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# ── Vetspire products query ───────────────────────────────────────────────────
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

def fetch_products_for_location(location_id):
    all_products = []
    offset = 0
    while True:
        result = gql(PRODUCTS_QUERY, {"locationId": location_id, "limit": 100, "offset": offset})
        if "errors" in result:
            err = result["errors"][0].get("message", str(result["errors"]))
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

# ── Pull products per location, keeping per-location membership ───────────────
print(f"\n=== Products Sync — {date.today()} ===")

# location_id → set of vetspire_product_ids enabled there this run
location_enabled: dict[str, set[str]] = {}

# vetspire_product_id → product dict (deduplicated for the products table upsert)
vs_id_to_product: dict[str, dict] = {}

for loc_id in LOCATION_IDS:
    print(f"  Fetching products for location {loc_id}…")
    products = fetch_products_for_location(loc_id)
    enabled_ids: set[str] = set()
    new_count = 0
    for p in products:
        vid = str(p.get("id") or "")
        if not vid:
            continue
        enabled_ids.add(vid)
        if vid not in vs_id_to_product:
            vs_id_to_product[vid] = p
            new_count += 1
    location_enabled[loc_id] = enabled_ids
    print(f"    {len(products)} products enabled, {new_count} new unique this location")

total_unique = len(vs_id_to_product)
print(f"\nTotal unique products across all locations: {total_unique}")

if not vs_id_to_product:
    print("No products found — exiting.")
    sys.exit(0)

# ── Upsert products table (keyed on vetspire_product_id) ─────────────────────
print("\nUpserting products table…")

now_iso = datetime.now(timezone.utc).isoformat()
records = []
for vid, p in vs_id_to_product.items():
    name = (p.get("name") or "").strip()
    if not name:
        continue
    ndc_raw = (p.get("ndc") or "").strip()
    records.append({
        "name":                name,
        "vetspire_product_id": vid,
        "sku":                 (p.get("sku") or "").strip() or None,
        "unit_cost":           p.get("unitCost") or None,
        "ndc":                 ndc_raw or None,
        "manufacturer":        ((p.get("manufacturer") or {}).get("name") or "").strip() or None,
    })

upserted = 0
failed   = 0
BATCH    = 100

for i in range(0, len(records), BATCH):
    batch = records[i:i+BATCH]
    try:
        status, body = supa_req(
            "POST",
            "/rest/v1/products?on_conflict=vetspire_product_id",
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

print(f"  Products upserted: {upserted}, failed: {failed}")

# ── Fetch product_id (uuid) for every vetspire_product_id we just upserted ───
print("\nFetching product UUIDs from Supabase…")

vs_id_to_uuid: dict[str, str] = {}
page_size = 500
offset = 0
while True:
    rows = supa_get(
        f"/rest/v1/products"
        f"?select=id,vetspire_product_id"
        f"&vetspire_product_id=not.is.null"
        f"&limit={page_size}&offset={offset}"
    )
    if not rows:
        break
    for row in rows:
        vid = row.get("vetspire_product_id")
        uid = row.get("id")
        if vid and uid:
            vs_id_to_uuid[str(vid)] = str(uid)
    if len(rows) < page_size:
        break
    offset += page_size

print(f"  {len(vs_id_to_uuid)} products with UUIDs loaded")

# ── Upsert product_locations — mark enabled for this run ─────────────────────
print("\nUpdating product_locations…")

loc_records = []
for loc_id, enabled_ids in location_enabled.items():
    for vid in enabled_ids:
        uuid = vs_id_to_uuid.get(vid)
        if not uuid:
            continue
        loc_records.append({
            "product_id":          uuid,
            "location_id":         loc_id,
            "vetspire_product_id": vid,
            "enabled":             True,
            "synced_at":           now_iso,
        })

loc_upserted = 0
loc_failed   = 0

for i in range(0, len(loc_records), BATCH):
    batch = loc_records[i:i+BATCH]
    try:
        status, body = supa_req(
            "POST",
            "/rest/v1/product_locations?on_conflict=product_id,location_id",
            batch,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        loc_upserted += len(batch)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  product_locations batch ✗ HTTP {e.code} — {body[:300]}")
        loc_failed += len(batch)
    except Exception as e:
        print(f"  product_locations batch ✗ {e}")
        loc_failed += len(batch)

print(f"  product_locations enabled: {loc_upserted}, failed: {loc_failed}")

# ── Disable products no longer seen at each location ─────────────────────────
# Any row in product_locations for a location in scope whose vetspire_product_id
# was NOT returned by Vetspire this run → set enabled=false.
print("\nDisabling products removed from Vetspire…")

disabled_total = 0

for loc_id in LOCATION_IDS:
    enabled_this_run = location_enabled.get(loc_id, set())

    # Fetch all currently-enabled rows for this location
    try:
        existing = supa_get(
            f"/rest/v1/product_locations"
            f"?select=product_id,vetspire_product_id"
            f"&location_id=eq.{loc_id}"
            f"&enabled=eq.true"
            f"&limit=2000"
        )
    except Exception as e:
        print(f"  Could not fetch existing rows for location {loc_id}: {e}")
        continue

    to_disable = [
        row for row in existing
        if row.get("vetspire_product_id") not in enabled_this_run
    ]

    if not to_disable:
        print(f"  Location {loc_id}: no deactivations")
        continue

    # Disable in batches by product_id list
    disable_ids = [row["product_id"] for row in to_disable]
    for i in range(0, len(disable_ids), BATCH):
        chunk = disable_ids[i:i+BATCH]
        id_list = ",".join(chunk)
        try:
            status, _ = supa_req(
                "PATCH",
                f"/rest/v1/product_locations"
                f"?location_id=eq.{loc_id}"
                f"&product_id=in.({id_list})",
                {"enabled": False, "synced_at": now_iso},
            )
            disabled_total += len(chunk)
        except urllib.error.HTTPError as e:
            print(f"  Disable batch error HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"  Disable batch error: {e}")

    print(f"  Location {loc_id}: {len(to_disable)} product(s) disabled")

print(f"  Total disabled this run: {disabled_total}")

# ── Backfill unit_cost from dispensed_items where products.unit_cost is null ──
# VetSpire's products API returns null for unitCost; use the most recent
# dispensed unit cost per product name as a reliable fallback.
print("\nBackfilling unit_cost from dispensed_items…")

# Fetch all products that still have no unit_cost (uuid → name)
no_cost_rows = supa_get(
    "/rest/v1/products"
    "?select=id,name"
    "&unit_cost=is.null"
    "&limit=2000"
)
print(f"  {len(no_cost_rows)} products with null unit_cost")

if no_cost_rows:
    # Fetch most-recent unit_cost per product_name from dispensed_items
    dispensed = supa_get(
        "/rest/v1/dispensed_items"
        "?select=product_name,unit_cost,dispensed_at"
        "&unit_cost=gt.0"
        "&order=dispensed_at.desc"
        "&limit=5000"
    )

    # Build name → latest cost map (dispensed_items are already ordered desc by time)
    name_to_cost: dict[str, float] = {}
    for row in dispensed:
        pn = (row.get("product_name") or "").strip().lower()
        uc = row.get("unit_cost")
        if pn and uc and pn not in name_to_cost:
            name_to_cost[pn] = float(uc)

    print(f"  {len(name_to_cost)} distinct product costs loaded from dispensed_items")

    cost_updated = 0
    cost_skipped = 0
    for row in no_cost_rows:
        uid  = row.get("id")
        name = (row.get("name") or "").strip().lower()
        cost = name_to_cost.get(name)
        if cost is None:
            cost_skipped += 1
            continue
        try:
            status, _ = supa_req(
                "PATCH",
                f"/rest/v1/products?id=eq.{uid}",
                {"unit_cost": cost},
            )
            cost_updated += 1
        except urllib.error.HTTPError as e:
            print(f"  Cost PATCH failed for {uid}: HTTP {e.code} — {e.read().decode()[:200]}")
        except Exception as e:
            print(f"  Cost PATCH error for {uid}: {e}")

    print(f"  unit_cost backfilled: {cost_updated}, no match: {cost_skipped}")

print(f"\n=== Done ===")
print(f"  {upserted} products upserted")
print(f"  {loc_upserted} location-product rows synced")
print(f"  {disabled_total} location-product rows disabled (mirrored from Vetspire)")
