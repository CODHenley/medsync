#!/usr/bin/env python3
"""
find_missing_skus.py
Lists all inventory-tracked products across all Scout locations that
have no SKU set in Vetspire. Outputs a CSV for easy review/upload.

Usage:
    python3 find_missing_skus.py
    (reads VETSPIRE_API_TOKEN env var, or ~/.vetspire_token)
"""
import sys, json, os, csv, urllib.request
from datetime import date

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

LOCATION_IDS = {
    "28250": "Lincoln Park",
    "28251": "Old Orchard",
    "28252": "West Loop",
    "28253": "Wheaton",
}

token = (
    os.environ.get("VETSPIRE_API_TOKEN")
    or (open(os.path.expanduser("~/.vetspire_token")).read().strip()
        if os.path.exists(os.path.expanduser("~/.vetspire_token")) else "")
).removeprefix("Bearer ").strip()

if not token:
    print("ERROR: No Vetspire token. Set VETSPIRE_API_TOKEN env var.")
    sys.exit(1)

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

QUERY = """
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
    ndc
    manufacturer { name }
    unitCost
  }
}
"""

print(f"=== Missing SKU Report — {date.today()} ===\n")

seen_ids = set()
all_products = []

for loc_id, loc_name in LOCATION_IDS.items():
    offset = 0
    loc_count = 0
    while True:
        result = gql(QUERY, {"locationId": loc_id, "limit": 100, "offset": offset})
        if "errors" in result:
            print(f"  Error for {loc_name}: {result['errors'][0].get('message')}")
            break
        page = (result.get("data") or {}).get("products") or []
        if not page:
            break
        for p in page:
            pid = str(p.get("id") or "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_products.append(p)
                loc_count += 1
        if len(page) < 100:
            break
        offset += 100
    print(f"  {loc_name}: {loc_count} unique inventory products fetched")

total = len(all_products)
missing_sku = [p for p in all_products if not (p.get("sku") or "").strip()]
has_ndc     = [p for p in missing_sku  if (p.get("ndc") or "").strip()]

print(f"\nTotal inventory-tracked products: {total}")
print(f"Missing SKU:                       {len(missing_sku)}")
print(f"  of which have NDC:               {len(has_ndc)}")
print(f"  of which have neither SKU/NDC:   {len(missing_sku) - len(has_ndc)}")

# ── Print to console ──────────────────────────────────────────────────────────
print(f"\n{'Product Name':<50} {'NDC':<18} {'Manufacturer':<25} {'Unit Cost'}")
print("-" * 110)
for p in sorted(missing_sku, key=lambda x: x.get("name") or ""):
    print(
        f"  {(p.get('name') or '')[:48]:<48}  "
        f"{(p.get('ndc') or ''):<18} "
        f"{((p.get('manufacturer') or {}).get('name') or '')[:23]:<25} "
        f"{p.get('unitCost') or ''}"
    )

# ── Write CSV ─────────────────────────────────────────────────────────────────
out_file = f"missing_skus_{date.today()}.csv"
with open(out_file, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["vetspire_id", "name", "ndc", "manufacturer", "unit_cost"])
    writer.writeheader()
    for p in sorted(missing_sku, key=lambda x: x.get("name") or ""):
        writer.writerow({
            "vetspire_id":  p.get("id") or "",
            "name":         p.get("name") or "",
            "ndc":          p.get("ndc") or "",
            "manufacturer": (p.get("manufacturer") or {}).get("name") or "",
            "unit_cost":    p.get("unitCost") or "",
        })

print(f"\nCSV saved → {out_file}  ({len(missing_sku)} rows)")
