#!/usr/bin/env python3
"""
Wheaton Nightly Revenue Pull
Runs at midnight via cron. Pulls today's revenue from Vetspire salesReport
and appends to wheaton_revenue_log.json for reliable COGS % calculations.

Token management:
  - Stores JWT in ~/.vetspire_token
  - Alerts if token is expired and needs refresh
  - To refresh: copy Bearer token from Vetspire DevTools → paste here:
      echo "eyJhbG..." > ~/.vetspire_token
"""

import json, urllib.request, urllib.error, os, sys
from datetime import date, datetime, timezone

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# ── Config ─────────────────────────────────────────────────────
ENDPOINT    = "https://api.vetspire.com/graphql"
WHEATON_ID  = "28253"
TOKEN_FILE  = os.path.expanduser("~/.vetspire_token")
LOG_FILE    = os.path.join(os.path.dirname(__file__), "wheaton_revenue_log.json")
ORIGIN      = "https://scoutcare.vetspire.com"

# ── Token management ───────────────────────────────────────────
def load_token():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: No token file found.")
        print(f"  Run:  echo 'YOUR_JWT_HERE' > {TOKEN_FILE}")
        print("  Get JWT: Vetspire → DevTools → Network → any graphql request → Headers → Authorization (copy value after 'Bearer ')")
        sys.exit(1)
    return open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

def check_token_expiry(token):
    try:
        payload = token.split(".")[1]
        # Pad base64
        payload += "=" * (4 - len(payload) % 4)
        import base64
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = data.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        if exp < now:
            hours_ago = (now - exp) / 3600
            print(f"ERROR: Token expired {hours_ago:.1f} hours ago.")
            print("  Refresh:  Open Vetspire in Chrome → DevTools → Network → any graphql request")
            print(f"            → Headers → Authorization → copy value after 'Bearer ' → paste:")
            print(f"            echo 'NEW_TOKEN' > {TOKEN_FILE}")
            sys.exit(1)
        hours_left = (exp - now) / 3600
        print(f"  Token valid for {hours_left:.1f} more hours")
    except Exception as e:
        print(f"  (Could not decode token expiry: {e})")

# ── GraphQL ────────────────────────────────────────────────────
def gql(token, query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Origin": ORIGIN,
        }
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

# ── Main ───────────────────────────────────────────────────────
def main():
    today = date.today().isoformat()
    print(f"\n=== Wheaton Revenue Pull — {today} ===")

    token = load_token()
    check_token_expiry(token)

    # Pull revenue
    print(f"  Querying salesReport for Wheaton (ID: {WHEATON_ID})...")
    r = gql(token,
        "query($lids:[ID!], $s:Date, $e:Date){ salesReport(locationIds:$lids, startDate:$s, endDate:$e) }",
        {"lids": [WHEATON_ID], "s": today, "e": today}
    )

    if "errors" in r:
        print(f"  ERROR from API: {r['errors']}")
        sys.exit(1)

    raw = r.get("data", {}).get("salesReport", "[]")
    records = json.loads(raw) if isinstance(raw, str) else raw

    if not records:
        print("  WARNING: No revenue data returned for today.")
        total = 0.0
    else:
        total = float(records[0].get("total", 0))

    print(f"  ✓ Wheaton revenue ({today}): ${total:,.2f}")

    # Load or create log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log = json.load(f)
    else:
        log = []

    # Update or append today's entry
    existing = next((e for e in log if e["date"] == today), None)
    entry = {
        "date": today,
        "location": "Wheaton",
        "location_id": WHEATON_ID,
        "revenue": total,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        log = [e if e["date"] != today else entry for e in log]
        print(f"  Updated existing entry for {today}")
    else:
        log.append(entry)
        print(f"  Appended new entry for {today}")

    # Sort by date desc
    log.sort(key=lambda x: x["date"], reverse=True)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"  Saved → {LOG_FILE}")

    # Upsert to Supabase daily_revenue
    print(f"  Upserting to Supabase daily_revenue...")
    supa_record = [{
        "date":          today,
        "location_id":   WHEATON_ID,
        "location_name": "Wheaton",
        "revenue":       total,
        "pulled_at":     datetime.now(timezone.utc).isoformat(),
    }]
    req2 = urllib.request.Request(
        SUPA_URL + "/rest/v1/daily_revenue",
        data=json.dumps(supa_record).encode(),
        headers={
            "Content-Type":  "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "resolution=merge-duplicates,return=minimal",
        }
    )
    req2.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req2, timeout=30) as r:
            print(f"  ✓ Supabase upsert OK (HTTP {r.status})")
    except urllib.error.HTTPError as e:
        print(f"  ✗ Supabase error {e.code}: {e.read().decode()[:200]}")

    print(f"\n  Last 7 days:")
    for e in log[:7]:
        print(f"    {e['date']}  ${e['revenue']:>10,.2f}")

    print("\nDone.\n")

if __name__ == "__main__":
    main()
