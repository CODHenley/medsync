#!/usr/bin/env python3
"""
Vetspire Inventory Probe — find on-hand stock level queries.
Run: python3 ~/Desktop/medsync_deploy/vetspire_inventory_probe.py
"""
import json, urllib.request, os

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"
ORIGIN     = "https://scoutcare.vetspire.com"
LOC_ID     = "28253"

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

def gql(label, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": ORIGIN,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        print(f"\n{'='*60}")
        print(f"PROBE: {label}")
        print(json.dumps(result, indent=2)[:1500])
    except Exception as e:
        print(f"\nPROBE {label} ERROR: {e}")

# Probe 1: inventoryItems
gql("inventoryItems", """
query($lid: ID!) {
    inventoryItems(locationId: $lid) {
        id name sku onHand reorderPoint
    }
}
""", {"lid": LOC_ID})

# Probe 2: products with inventory
gql("products(locationId)", """
query($lid: ID!) {
    products(locationId: $lid) {
        id name sku onHand quantityOnHand unitCost reorderPoint minimum maximum
    }
}
""", {"lid": LOC_ID})

# Probe 3: inventory query
gql("inventory(locationId)", """
query($lid: ID!) {
    inventory(locationId: $lid) {
        productId productName onHand minimum maximum
    }
}
""", {"lid": LOC_ID})

# Probe 4: stockLevels
gql("stockLevels", """
query($lids: [ID!]) {
    stockLevels(locationIds: $lids) {
        productId productName quantity reorderPoint
    }
}
""", {"lids": [LOC_ID]})

# Probe 5: inventoryReport
gql("inventoryReport", """
query($lids: [ID!]) {
    inventoryReport(locationIds: $lids) {
        productId productName onHand minimum maximum unitCost
    }
}
""", {"lids": [LOC_ID]})

# Probe 6: schema — look for inventory-related root queries
gql("__schema inventory fields", """
{
    __schema {
        queryType {
            fields {
                name
                description
            }
        }
    }
}
""")
