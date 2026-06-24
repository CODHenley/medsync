#!/usr/bin/env python3
"""
One-time backfill — pulls the last 90 days of Wheaton daily revenue
from Vetspire salesReport and upserts to Supabase daily_revenue table.
Run once manually; nightly script handles daily pulls going forward.
"""

import json, urllib.request, urllib.error, os, sys, base64
from datetime import date, datetime, timezone, timedelta

TOKEN_FILE        = os.path.expanduser("~/.vetspire_token")
VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN   = "https://scoutcare.vetspire.com"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
WHEATON_ID        = "28253"
BACKFILL_DAYS     = 90

raw_token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
try:
    payload = raw_token.split(".")[1] + "=="
    data = json.loads(base64.urlsafe_b64decode(payload))
    exp = data.get("exp", 0)
    now = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print("TOKEN EXPIRED — refresh it first"); sys.exit(1)
    print(f"Token valid for {(exp-now)/3600:.1f}h")
except Exception as e:
    print(f"Token loaded: {raw_token[:20]}...")

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e)
}
"""

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": raw_token,
        "Origin":        VETSPIRE_ORIGIN,
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

print(f"\nBackfilling {BACKFILL_DAYS} days of revenue: {start_date} → {today}\n")

total_days   = 0
total_revenue = 0.0
cursor = start_date

while cursor <= today:
    s = cursor.isoformat()
    e = cursor.isoformat()  # one day at a time for accurate daily revenue

    try:
        r = gql(SALES_QUERY, {"lids": [WHEATON_ID], "s": s, "e": e})
    except Exception as ex:
        print(f"  {s}: ERROR — {ex}")
        cursor += timedelta(days=1)
        continue

    if "errors" in r:
        print(f"  {s}: API error — {r['errors'][0]['message'][:100]}")
        cursor += timedelta(days=1)
        continue

    raw = r.get("data", {}).get("salesReport", "[]")
    records = json.loads(raw) if isinstance(raw, str) else (raw or [])
    revenue = float(records[0].get("total", 0)) if records else 0.0

    status = supa_upsert([{
        "date":          s,
        "location_id":   WHEATON_ID,
        "location_name": "Wheaton",
        "revenue":       revenue,
        "pulled_at":     datetime.now(timezone.utc).isoformat(),
    }])

    if str(status).startswith("2"):
        print(f"  {s}  ${revenue:>10,.2f}  ✓")
        total_days    += 1
        total_revenue += revenue
    else:
        print(f"  {s}  ✗ (status {status})")

    cursor += timedelta(days=1)

print(f"\n{'='*45}")
print(f"Backfill complete!")
print(f"  Days upserted : {total_days}")
print(f"  Total revenue : ${total_revenue:,.2f}")
print(f"  Avg/day       : ${total_revenue/max(total_days,1):,.2f}")
