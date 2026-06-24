#!/usr/bin/env python3
"""
vetspire_vaccine_lot_sync.py
Sync vaccine lot numbers and expiration dates from Vetspire into MedSync lots table.

Vetspire exposes vaccine lot/exp data through patient vaccination records.
This script probes several known query shapes, uses whichever works, and
upserts into the lots table so vaccines appear on the Lot Lifecycle screen.

Usage:
    python3 vetspire_vaccine_lot_sync.py
    (reads ~/.vetspire_token)
"""
import sys, json, os, urllib.request
from datetime import date, datetime, timezone

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = [
    {"vetspire_id": "28253", "name": "Wheaton",      "uuid": "11111111-0000-0000-0000-000000000004"},
    {"vetspire_id": "28250", "name": "Lincoln Park",  "uuid": "11111111-0000-0000-0000-000000000001"},
    {"vetspire_id": "28251", "name": "Old Orchard",   "uuid": "11111111-0000-0000-0000-000000000002"},
    {"vetspire_id": "28252", "name": "West Loop",     "uuid": "11111111-0000-0000-0000-000000000003"},
]

# Vetspire token — send without "Bearer " prefix (same as wheaton_usage_backfill.py)
token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
print(f"Token loaded: {token[:20]}...")

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": token,   # no "Bearer " prefix — matches working backfill
        "Origin": VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def supa(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    req = urllib.request.Request(SUPA_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status

# ── Probe schema for vaccination-related queries (skip if introspection disabled) ──
print("\n=== Probing Vetspire schema for vaccination queries ===")
try:
    r = gql('{ __schema { queryType { fields { name } } } }')
    fields = r.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
    vacc_names = [f["name"] for f in fields if any(k in f["name"].lower() for k in ["vaccin", "lot", "immuniz"])]
    print(f"  Vaccine-related queries found: {vacc_names or 'none'}")
    all_names = [f["name"] for f in fields]
    print(f"  Total queries available: {len(all_names)}")
except Exception as e:
    print(f"  Introspection not available: {e}")
    all_names = []

# ── Attempt 1: vaccinations query ────────────────────────────────────────────
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

# ── Attempt 2: patientVaccinations ───────────────────────────────────────────
PVACC_QUERY = """
query($lid: ID!) {
    patientVaccinations(locationId: $lid, first: 200) {
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

# ── Attempt 3: inventoryLots ─────────────────────────────────────────────────
INVLOTS_QUERY = """
query($lid: ID!) {
    inventoryLots(locationId: $lid, first: 200) {
        edges { node {
            id
            lotNumber
            expirationDate
            product { id name }
            quantity
        }}
    }
}
"""

today_str = date.today().isoformat()
upserted = 0
skipped = 0

for loc in LOCATIONS:
    print(f"\n=== {loc['name']} (vetspire_id={loc['vetspire_id']}) ===")
    nodes = []
    source = None

    for (label, query, conn_key) in [
        ("vaccinations",       VACC_QUERY,    "vaccinations"),
        ("patientVaccinations",PVACC_QUERY,   "patientVaccinations"),
        ("inventoryLots",      INVLOTS_QUERY, "inventoryLots"),
    ]:
        try:
            result = gql(query, {"lid": loc["vetspire_id"]})
            if "errors" in result:
                print(f"  {label}: {result['errors'][0].get('message','error')}")
                continue
            conn = (result.get("data") or {}).get(conn_key) or {}
            edges = conn.get("edges") or []
            nodes = [e["node"] for e in edges if e.get("node")]
            print(f"  {label}: {len(nodes)} records")
            source = label

            # Handle pagination for vaccinations
            page_info = conn.get("pageInfo") or {}
            cursor = page_info.get("endCursor")
            while page_info.get("hasNextPage") and cursor:
                try:
                    r2 = gql(query, {"lid": loc["vetspire_id"], "after": cursor})
                    conn2 = (r2.get("data") or {}).get(conn_key) or {}
                    edges2 = conn2.get("edges") or []
                    more = [e["node"] for e in edges2 if e.get("node")]
                    nodes.extend(more)
                    page_info = conn2.get("pageInfo") or {}
                    cursor = page_info.get("endCursor")
                except Exception:
                    break
            break
        except Exception as e:
            print(f"  {label}: failed — {e}")

    if not nodes:
        print("  No vaccination/lot data found via any query")
        continue

    print(f"  {len(nodes)} total records from {source}")

    # Deduplicate by (product_id, lot_number)
    lot_map = {}
    for node in nodes:
        lot_num = (node.get("lotNumber") or "").strip()
        exp_raw = (node.get("expirationDate") or "").strip()
        prod = node.get("product") or {}
        pid = str(prod.get("id") or "")
        pname = prod.get("name") or ""
        if not lot_num or not exp_raw or not pid:
            skipped += 1
            continue
        key = (pid, lot_num)
        if not lot_map.get(key) or (node.get("administeredOn") or "") > (lot_map[key].get("administeredOn") or ""):
            lot_map[key] = node

    print(f"  {len(lot_map)} unique (product, lot) pairs")

    records = []
    for (pid, lot_num), node in lot_map.items():
        exp_raw = (node.get("expirationDate") or "").strip()
        prod = node.get("product") or {}
        pname = prod.get("name") or ""
        administered = node.get("administeredOn") or today_str

        exp_date = None
        if len(exp_raw) == 10 and "-" in exp_raw:
            exp_date = exp_raw
        elif len(exp_raw) == 7 and "/" in exp_raw:
            mm, yyyy = exp_raw.split("/")
            exp_date = f"{yyyy}-{mm}-01"
        elif len(exp_raw) >= 7 and "-" in exp_raw:
            try:
                parts = exp_raw[:7].split("-")
                exp_date = f"{parts[0]}-{parts[1]}-01"
            except Exception:
                pass

        if not exp_date:
            skipped += 1
            continue

        try:
            exp_dt = date.fromisoformat(exp_date)
            days_left = (exp_dt - date.today()).days
            status = "Expired" if days_left < 0 else "Expiring soon" if days_left <= 30 else "Active"
        except Exception:
            status = "Active"

        records.append({
            "location_id":     loc["uuid"],
            "lot_number":      lot_num,
            "expiration_date": exp_date,
            "received_date":   administered,
            "qty_received":    0,
            "qty_remaining":   0,
            "status":          status,
            "notes":           f"Synced from Vetspire {source}: {pname}",
            "vendor":          None,
        })

    if not records:
        print("  Nothing to upsert (no records had both lot # and exp date)")
        continue

    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        try:
            supa("POST", "/rest/v1/lots?on_conflict=location_id,lot_number", batch)
            upserted += len(batch)
        except Exception as e:
            print(f"  Upsert error: {e}")

    print(f"  Upserted {len(records)} records")

print(f"\n=== Done — {upserted} upserted, {skipped} skipped ===")
