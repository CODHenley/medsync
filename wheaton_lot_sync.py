#!/usr/bin/env python3
"""
wheaton_lot_sync.py
Sync all active medication lots and expiration dates from Vetspire into
the MedSync lots table for Wheaton.

Source: Vetspire inventoryAdjustments query (plain list, not Connection).
Each adjustment record has lotNumber, expirationDate, quantityChange, product.
We sum quantityChange per (product, lot) to find what's currently in stock,
then upsert into the lots table.

Usage:
    python3 wheaton_lot_sync.py
    (reads ~/.vetspire_token)
"""
import sys, json, os, urllib.request, urllib.parse
from datetime import date, datetime

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

WHEATON_VETSPIRE_ID = "28253"
WHEATON_UUID = "11111111-0000-0000-0000-000000000004"

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
print(f"Token: {token[:20]}...")

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
        body_out = r.read()
        return r.status, body_out

def supa_get(path):
    headers = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
    }
    req = urllib.request.Request(SUPA_URL + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def get_or_create_product_id(name):
    """Look up product by name in Supabase products table; create if missing."""
    encoded_name = urllib.parse.quote(name)
    rows = supa_get(f"/rest/v1/products?name=eq.{encoded_name}&select=id")
    if rows:
        return rows[0]["id"]
    # Create minimal product record
    status, body = supa_req("POST", "/rest/v1/products", {"name": name}, prefer="return=representation")
    created = json.loads(body)
    if isinstance(created, list) and created:
        return created[0]["id"]
    raise RuntimeError(f"Failed to create product '{name}': {body.decode()}")

# ── Fetch all inventory adjustments for Wheaton ──────────────────────────────
# inventoryAdjustments returns a plain list (not a Connection) — no edges wrapper.
# Probe confirmed fields: expirationDate, lotNumber, product { id name },
#                         quantityChange, insertedAt, isWastage, reason

QUERY = """
query($lid: ID!) {
    inventoryAdjustments(locationId: $lid) {
        id
        lotNumber
        expirationDate
        quantityChange
        insertedAt
        isWastage
        product { id name }
    }
}
"""

print(f"\nFetching inventory adjustments for Wheaton (id={WHEATON_VETSPIRE_ID})...")

all_adjustments = []
try:
    result = gql(QUERY, {"lid": WHEATON_VETSPIRE_ID})
    if "errors" in result:
        err = result["errors"][0].get("message", "?")
        print(f"  GraphQL error: {err}")
        sys.exit(1)
    all_adjustments = (result.get("data") or {}).get("inventoryAdjustments") or []
    print(f"  Fetched {len(all_adjustments)} adjustments")
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

print(f"\nTotal adjustments fetched: {len(all_adjustments)}")

# ── Aggregate by (product_id, lot_number) ────────────────────────────────────
# Sum quantityChange to get net stock per lot. Keep expiration date and product name.
lot_map = {}  # key: (product_id, lot_number) → {qty, exp_date, product_name, last_date}

skipped_no_lot = 0
skipped_no_exp = 0

for adj in all_adjustments:
    lot_num = (adj.get("lotNumber") or "").strip()
    exp_raw = (adj.get("expirationDate") or "").strip()
    prod = adj.get("product") or {}
    pid = str(prod.get("id") or "")
    pname = prod.get("name") or ""
    qty_change = float(adj.get("quantityChange") or 0)
    inserted = adj.get("insertedAt") or ""

    if not lot_num:
        skipped_no_lot += 1
        continue
    if not exp_raw:
        skipped_no_exp += 1
        continue
    if not pid:
        continue

    key = (pid, lot_num)
    if key not in lot_map:
        lot_map[key] = {
            "product_id": pid,
            "product_name": pname,
            "lot_number": lot_num,
            "exp_raw": exp_raw,
            "qty_net": 0.0,
            "last_date": inserted,
        }
    lot_map[key]["qty_net"] += qty_change
    if inserted > lot_map[key]["last_date"]:
        lot_map[key]["last_date"] = inserted
        lot_map[key]["exp_raw"] = exp_raw  # use most recent exp date for this lot

print(f"\nAggregation:")
print(f"  {skipped_no_lot} adjustments skipped (no lot number)")
print(f"  {skipped_no_exp} adjustments skipped (no expiration date)")
print(f"  {len(lot_map)} unique (product, lot) combinations")

# Show what we have
in_stock = [(k, v) for k, v in lot_map.items() if v["qty_net"] > 0]
depleted = [(k, v) for k, v in lot_map.items() if v["qty_net"] <= 0]
print(f"  {len(in_stock)} lots currently in stock (qty > 0)")
print(f"  {len(depleted)} lots depleted/returned (qty ≤ 0)")

# ── Parse expiration dates and build records (in-stock lots only) ─────────────
lot_map = {k: v for k, v in lot_map.items() if v["qty_net"] > 0}
today = date.today()
records = []
skipped_bad_exp = 0

for key, lot in lot_map.items():
    exp_raw = lot["exp_raw"]
    exp_date = None

    # Try common formats: YYYY-MM-DD, YYYY-MM, MM/YYYY, MM/YYYY
    if len(exp_raw) == 10 and exp_raw[4] == "-":
        exp_date = exp_raw  # YYYY-MM-DD
    elif len(exp_raw) == 7 and exp_raw[4] == "-":
        exp_date = exp_raw + "-01"  # YYYY-MM → YYYY-MM-01
    elif len(exp_raw) == 7 and "/" in exp_raw:
        mm, yyyy = exp_raw.split("/")
        exp_date = f"{yyyy}-{mm.zfill(2)}-01"  # MM/YYYY
    elif len(exp_raw) >= 7:
        try:
            parts = exp_raw[:7].split("-")
            if len(parts) == 2:
                exp_date = f"{parts[0]}-{parts[1]}-01"
        except Exception:
            pass

    if not exp_date:
        skipped_bad_exp += 1
        continue

    try:
        exp_dt = date.fromisoformat(exp_date)
        days_left = (exp_dt - today).days
        if days_left < 0:
            status = "Expired"
        elif days_left <= 30:
            status = "Expiring soon"
        else:
            status = "Active"
    except Exception:
        status = "Active"
        exp_dt = today

    # received_date: earliest adjustment date for this lot
    received = (lot["last_date"] or today.isoformat())[:10]

    records.append({
        "location_id":     WHEATON_UUID,
        "lot_number":      lot["lot_number"],
        "expiration_date": exp_date,
        "received_date":   received,
        "qty_received":    0,
        "qty_remaining":   max(0, int(round(lot["qty_net"]))),
        "status":          status,
        "notes":           f"Vetspire inventory: {lot['product_name']}",
        "vendor":          None,
    })

print(f"  {skipped_bad_exp} lots skipped (unparseable expiration date)")
print(f"\n{len(records)} records to upsert")

if not records:
    print("Nothing to upsert.")
    sys.exit(0)

# Preview
print(f"\n{'Product':<45} {'Lot':<15} {'Exp':<12} {'Qty':>6} Status")
print("-" * 100)
for r in sorted(records, key=lambda x: x["expiration_date"]):
    pname = r["notes"].replace("Vetspire inventory: ", "")
    print(f"  {pname:<43} {r['lot_number']:<15} {r['expiration_date']:<12} {r['qty_remaining']:>6}  {r['status']}")

# ── Sync into Supabase lots table (delete Vetspire-synced rows, then insert) ──
print(f"\nSyncing {len(records)} records into lots table...")

# Delete all existing Vetspire-synced lots for Wheaton (notes starts with "Vetspire inventory:")
try:
    supa_req("DELETE", f"/rest/v1/lots?location_id=eq.{WHEATON_UUID}&notes=like.Vetspire%20inventory%3A%25")  # noqa
    print("  Cleared existing Vetspire lots for Wheaton")
except Exception as e:
    print(f"  Warning: delete step failed — {e}")

upserted = 0
failed = 0

for i in range(0, len(records), 50):
    batch = records[i:i+50]
    try:
        http_status, _ = supa_req("POST", "/rest/v1/lots", batch)
        upserted += len(batch)
        print(f"  Batch {i//50 + 1}: ✓ {len(batch)} records (HTTP {http_status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Batch {i//50 + 1}: ✗ HTTP {e.code} — {body[:200]}")
        failed += len(batch)
    except Exception as e:
        print(f"  Batch {i//50 + 1}: ✗ {e}")
        failed += len(batch)

print(f"\n=== Done — {upserted} upserted, {failed} failed ===")
print("Refresh the Lot Lifecycle screen to see updated lots.")
