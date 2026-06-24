#!/usr/bin/env python3
"""
One-time backfill — pulls the last 90 days of daily revenue for all 4 Scout
locations from Vetspire salesReport and upserts to Supabase daily_revenue table.
Run once manually; nightly_revenue_sync.py handles daily pulls going forward.

Usage:
  python3 all_locations_revenue_backfill.py
  (reads token from vetspire_token.txt in same directory, or ~/.vetspire_token)
"""

import json, urllib.request, urllib.error, os, sys
from datetime import date, datetime, timezone, timedelta

VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
BACKFILL_DAYS     = 90

LOCATIONS = [
    ("Lincoln Park", "23083"),
    ("Old Orchard",  "27390"),
    ("West Loop",    "24356"),
    ("Wheaton",      "28253"),
]

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e)
}
"""

# Load token — prefer local file, fall back to ~/.vetspire_token
_script_dir = os.path.dirname(os.path.abspath(__file__))
_local_token = os.path.join(_script_dir, "vetspire_token.txt")
_home_token  = os.path.expanduser("~/.vetspire_token")
if os.path.exists(_local_token):
    raw_token = open(_local_token).read().strip().removeprefix("Bearer ").strip()
    print(f"Token: {raw_token[:20]}…")
elif os.path.exists(_home_token):
    raw_token = open(_home_token).read().strip().removeprefix("Bearer ").strip()
    print(f"Token: {raw_token[:20]}…")
else:
    raise SystemExit("ERROR: No token file found. Add vetspire_token.txt to the script directory.")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": raw_token,
        "Origin":        "https://scoutcare.vetspire.com",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def supa_upsert(records):
    if not records:
        return 201
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/daily_revenue",
        data=body,
        headers={
            "Content-Type":  "application/json",
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

today      = date.today()
start_date = today - timedelta(days=BACKFILL_DAYS)

print(f"\nBackfilling {BACKFILL_DAYS} days: {start_date} → {today}")
print(f"Locations: {', '.join(n for n, _ in LOCATIONS)}\n")

grand_days    = 0
grand_revenue = 0.0

for loc_name, loc_id in LOCATIONS:
    print(f"{'='*50}")
    print(f"  {loc_name} ({loc_id})")
    print(f"{'='*50}")

    loc_days    = 0
    loc_revenue = 0.0
    cursor      = start_date

    while cursor <= today:
        s = cursor.isoformat()

        try:
            r = gql(SALES_QUERY, {"lids": [loc_id], "s": s, "e": s})
        except Exception as ex:
            print(f"  {s}: ERROR — {ex}")
            cursor += timedelta(days=1)
            continue

        if "errors" in r:
            print(f"  {s}: API error — {r['errors'][0]['message'][:100]}")
            cursor += timedelta(days=1)
            continue

        raw     = r.get("data", {}).get("salesReport", "[]")
        records = json.loads(raw) if isinstance(raw, str) else (raw or [])
        rec     = records[0] if records else {}
        revenue = float(rec.get("collected") or rec.get("paid") or rec.get("paidTotal") or rec.get("total") or 0)

        status = supa_upsert([{
            "date":          s,
            "location_id":   loc_id,
            "location_name": loc_name,
            "revenue":       revenue,
            "pulled_at":     datetime.now(timezone.utc).isoformat(),
        }])

        if str(status).startswith("2"):
            print(f"  {s}  ${revenue:>10,.2f}  ✓")
            loc_days    += 1
            loc_revenue += revenue
        else:
            print(f"  {s}  ✗ (status {status})")

        cursor += timedelta(days=1)

    print(f"  → {loc_days} days, ${loc_revenue:,.2f} total, ${loc_revenue/max(loc_days,1):,.2f}/day avg\n")
    grand_days    += loc_days
    grand_revenue += loc_revenue

print(f"{'='*50}")
print(f"All locations complete!")
print(f"  Total days upserted : {grand_days}")
print(f"  Total revenue       : ${grand_revenue:,.2f}")
