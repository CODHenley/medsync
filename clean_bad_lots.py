#!/usr/bin/env python3
"""
clean_bad_lots.py
Removes known seed/test lot data from Scout's Wheaton location.
Run once: python3 clean_bad_lots.py
"""
import urllib.request, json

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIzMzAzNjUsImV4cCI6MjA1NzkwNjM2NX0.dn3rNg0_qC-YNHCIBUorlBqhqpvbVnXn0ckMoMLxDsQ"
WHEATON_UUID = "11111111-0000-0000-0000-000000000004"

HEADERS = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json",
}

# ── Step 1: show all Wheaton lots so we can review ───────────────────────────
print("=== All lots currently in Wheaton ===")
req = urllib.request.Request(
    SUPA_URL + f"/rest/v1/lots?location_id=eq.{WHEATON_UUID}&select=id,lot_number,notes,status&order=lot_number.asc",
    headers=HEADERS
)
with urllib.request.urlopen(req, timeout=15) as r:
    rows = json.loads(r.read())

for row in rows:
    print(f"  {row['lot_number']:<12}  {row['status']:<15}  {(row.get('notes') or '')[:60]}")
print(f"\n  Total: {len(rows)} lots\n")

# ── Step 2: delete known bad lots (seed data not from Scout) ─────────────────
# Tramadol is not carried at Wheaton — LOT-0029 is seed data
BAD_LOT_NUMBERS = ["LOT-0029"]

print("=== Deleting bad lots ===")
for lot_num in BAD_LOT_NUMBERS:
    url = SUPA_URL + f"/rest/v1/lots?lot_number=eq.{lot_num}&location_id=eq.{WHEATON_UUID}"
    req = urllib.request.Request(url, method="DELETE", headers={**HEADERS, "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=15) as r:
        deleted = json.loads(r.read())
    if deleted:
        print(f"  Deleted: {lot_num} ({deleted[0].get('notes','')[:50]})")
    else:
        print(f"  {lot_num} — not found (already deleted?)")

print("\nDone. Run 'Refresh' on the Lot Lifecycle screen to confirm.")
