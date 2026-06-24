#!/usr/bin/env python3
"""
vetspire_vaccine_lot_sync.py
Sync vaccine lot numbers and expiration dates from Vetspire into MedSync lots table.

Vetspire stores lot # and exp date on patient vaccination records.
This script queries all Scout locations, finds the most recent lot entry
per vaccine product, and upserts into the lots table.

Usage:
    python3 vetspire_vaccine_lot_sync.py
    (reads ~/.vetspire_token)
"""
import sys, json, os, urllib.request
from datetime import date, datetime, timezone

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIzMzAzNjUsImV4cCI6MjA1NzkwNjM2NX0.dn3rNg0_qC-YNHCIBUorlBqhqpvbVnXn0ckMoMLxDsQ"

LOCATIONS = [
    {"vetspire_id": "28253", "name": "Wheaton",     "uuid": "11111111-0000-0000-0000-000000000004"},
    {"vetspire_id": "28250", "name": "Lincoln Park", "uuid": "11111111-0000-0000-0000-000000000001"},
    {"vetspire_id": "28251", "name": "Old Orchard",  "uuid": "11111111-0000-0000-0000-000000000002"},
    {"vetspire_id": "28252", "name": "West Loop",    "uuid": "11111111-0000-0000-0000-000000000003"},
]

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": "https://scoutcare.vetspire.com",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def supa(method, path, body=None, extra_headers=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(SUPA_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status

# ── First: probe Vetspire schema for vaccination fields ──────────────────────
print("=== Probing Vetspire vaccination schema ===")
try:
    r = gql('{ __type(name: "Vaccination") { fields { name type { name kind ofType { name } } } } }')
    vacc_fields = r.get("data", {}).get("__type", {}).get("fields", [])
    if vacc_fields:
        print("  Vaccination type fields:")
        for f in vacc_fields:
            print(f"    {f['name']}")
    else:
        print("  No 'Vaccination' type found — trying alternate names...")
        # Check query fields for vaccination-related queries
        r2 = gql('{ __schema { queryType { fields { name description } } } }')
        qfields = r2.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
        vacc_queries = [f for f in qfields if any(k in f["name"].lower() for k in ["vaccin", "lot", "immuniz"])]
        for f in vacc_queries:
            print(f"  Query: {f['name']} — {f.get('description','')}")
except Exception as e:
    print(f"  Schema probe failed: {e}")

# ── Query vaccinations per location ─────────────────────────────────────────
VACC_QUERY = """
query($lid: ID!, $after: String) {
    vaccinations(locationId: $lid, first: 200, after: $after) {
        pageInfo { hasNextPage endCursor }
        edges { node {
            id
            lotNumber
            expirationDate
            administeredOn
            product { id name }
        }}
    }
}
"""

today_str = date.today().isoformat()
upserted = 0
skipped = 0

for loc in LOCATIONS:
    print(f"\n=== {loc['name']} (vetspire_id={loc['vetspire_id']}) ===")
    # Collect all vaccinations, paginating
    all_nodes = []
    cursor = None
    page = 0
    while True:
        try:
            variables = {"lid": loc["vetspire_id"]}
            if cursor:
                variables["after"] = cursor
            result = gql(VACC_QUERY, variables)
        except Exception as e:
            print(f"  ERROR fetching page {page}: {e}")
            break

        if "errors" in result:
            err = result["errors"][0].get("message", "unknown")
            print(f"  API error: {err}")
            break

        conn = (result.get("data") or {}).get("vaccinations") or {}
        edges = conn.get("edges") or []
        nodes = [e["node"] for e in edges if e.get("node")]
        all_nodes.extend(nodes)
        page_info = conn.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        page += 1

    print(f"  {len(all_nodes)} vaccination records")

    # Deduplicate: per (product_id, lot_number) keep the record with the latest administeredOn
    # so each physical lot bottle appears once
    lot_map = {}  # (product_id, lot_number) -> node
    for node in all_nodes:
        lot_num = (node.get("lotNumber") or "").strip()
        exp_raw = (node.get("expirationDate") or "").strip()
        prod = node.get("product") or {}
        pid = str(prod.get("id") or "")
        pname = prod.get("name") or ""

        if not lot_num or not exp_raw or not pid:
            skipped += 1
            continue

        key = (pid, lot_num)
        existing = lot_map.get(key)
        if not existing:
            lot_map[key] = node
        else:
            # Keep more recent administeredOn
            if (node.get("administeredOn") or "") > (existing.get("administeredOn") or ""):
                lot_map[key] = node

    print(f"  {len(lot_map)} unique (product, lot) pairs with lot # and exp date")

    # Build lots records and upsert
    records = []
    for (pid, lot_num), node in lot_map.items():
        exp_raw = (node.get("expirationDate") or "").strip()
        prod = node.get("product") or {}
        pname = prod.get("name") or ""
        administered = node.get("administeredOn") or today_str

        # Parse expiration: Vetspire may return YYYY-MM-DD or MM/YYYY
        exp_date = None
        if len(exp_raw) == 10 and exp_raw[4] == "-":
            # YYYY-MM-DD
            exp_date = exp_raw
        elif len(exp_raw) == 7 and exp_raw[2] == "/":
            # MM/YYYY → first of that month
            mm, yyyy = exp_raw.split("/")
            exp_date = f"{yyyy}-{mm}-01"
        elif len(exp_raw) >= 7:
            # Try YYYY-MM or other partial
            try:
                parts = exp_raw[:7].split("-")
                exp_date = f"{parts[0]}-{parts[1]}-01"
            except Exception:
                exp_date = None

        if not exp_date:
            skipped += 1
            continue

        # Determine status from expiration
        try:
            exp_dt = date.fromisoformat(exp_date)
            days_left = (exp_dt - date.today()).days
            if days_left < 0:
                status = "Expired"
            elif days_left <= 30:
                status = "Expiring soon"
            else:
                status = "Active"
        except Exception:
            status = "Active"

        records.append({
            "location_id":      loc["uuid"],
            "lot_number":       lot_num,
            "expiration_date":  exp_date,
            "received_date":    administered,
            "qty_received":     0,   # vaccines tracked by patient record, not bulk inventory
            "qty_remaining":    0,
            "status":           status,
            "notes":            f"Synced from Vetspire vaccination records: {pname}",
            "vendor":           None,
        })

    if not records:
        print("  Nothing to upsert")
        continue

    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            status_code = supa("POST", "/rest/v1/lots?on_conflict=location_id,lot_number", batch)
            upserted += len(batch)
        except Exception as e:
            print(f"  Upsert error (batch {i//batch_size}): {e}")

    print(f"  Upserted {len(records)} lot records")

print(f"\n=== Done — {upserted} upserted, {skipped} skipped (missing lot/exp/product) ===")
