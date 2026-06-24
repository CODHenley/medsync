#!/usr/bin/env python3
"""
probe_inventory_lots.py
Probe Vetspire for inventory lot/expiration data for all medications at Wheaton.
Runs schema introspection to find the right query, then samples it.
"""
import json, os, urllib.request

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
WHEATON_ID = "28253"

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
print(f"Token: {token[:20]}...")

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def try_query(label, q, variables=None):
    print(f"\n--- {label} ---")
    try:
        r = gql(q, variables or {})
        if "errors" in r:
            print(f"  ERROR: {r['errors'][0].get('message','?')}")
            return None
        data = r.get("data")
        # For introspection, just print field names cleanly
        typ = (data or {}).get("__type")
        if typ and typ.get("fields"):
            for f in typ["fields"]:
                tname = (f.get("type") or {}).get("name") or \
                        ((f.get("type") or {}).get("ofType") or {}).get("name") or "?"
                print(f"  {f['name']}: {tname}")
            return data
        print(json.dumps(data, indent=2)[:3000])
        return data
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None

# 1. Find all inventory/lot/product/stock related queries
print("\n=== Schema: inventory/lot/product/stock queries ===")
r = gql('{ __schema { queryType { fields { name description } } } }')
fields = r["data"]["__schema"]["queryType"]["fields"]
keywords = ["inventor", "lot", "stock", "product", "item", "supply", "drug", "medic", "dispens", "catalog"]
matches = []
for f in fields:
    name = f.get("name","").lower()
    desc = (f.get("description") or "").lower()
    if any(k in name or k in desc for k in keywords):
        matches.append(f)
        print(f"  {f['name']}: {(f.get('description') or '')[:80]}")

print(f"\n  ({len(matches)} matches out of {len(fields)} total queries)")

# 2. Probe inventory-related queries
try_query("products(locationId)", """
query { products(locationId: """ + WHEATON_ID + """, first: 3) {
    edges { node {
        id name sku
        lots { lotNumber expirationDate quantity }
    }}
}}
""")

try_query("inventoryItems(locationId)", """
query { inventoryItems(locationId: """ + WHEATON_ID + """, first: 3) {
    edges { node {
        id
        lotNumber
        expirationDate
        quantity
        product { id name }
    }}
}}
""")

try_query("inventoryAdjustments(locationId)", """
query { inventoryAdjustments(locationId: """ + WHEATON_ID + """, first: 3) {
    edges { node {
        id
        lotNumber
        expirationDate
        quantity
        product { id name }
    }}
}}
""")

try_query("introspect InventoryAdjustment type", """
{
  __type(name: "InventoryAdjustment") {
    fields { name description type { name kind ofType { name kind } } }
  }
}
""")

try_query("inventoryAdjustment(locationId)", """
query { inventoryAdjustment(locationId: """ + WHEATON_ID + """, first: 3) {
    edges { node {
        id
        lotNumber
        expirationDate
        quantity
        product { id name }
    }}
}}
""")

# 3. Probe product type for lot fields
try_query("products with all fields", """
query { products(locationId: """ + WHEATON_ID + """, first: 1) {
    edges { node {
        id name sku
        inventoryItems { id lotNumber expirationDate quantity }
    }}
}}
""")

try_query("products inventoryCount", """
query { products(locationId: """ + WHEATON_ID + """, first: 3, inStock: true) {
    edges { node {
        id name sku
        inventoryCount
        inventoryItems { lotNumber expirationDate quantity }
    }}
}}
""")

# 4. Check what fields InventoryItem/Product type has
try_query("introspect Product type", """
{
  __type(name: "Product") {
    fields { name description type { name kind ofType { name kind } } }
  }
}
""")

try_query("introspect InventoryItem type", """
{
  __type(name: "InventoryItem") {
    fields { name description type { name kind ofType { name kind } } }
  }
}
""")

try_query("introspect Lot type", """
{
  __type(name: "Lot") {
    fields { name description type { name kind ofType { name kind } } }
  }
}
""")
