#!/usr/bin/env python3
"""
MedSync — Nightly Revenue Sync
Pulls yesterday's revenue from Vetspire salesReport for all 4 Scout locations
and upserts to Supabase daily_revenue table.

Runs nightly via GitHub Actions. Uses VETSPIRE_API_TOKEN (permanent API key,
same auth pattern as wheaton_lot_sync.py — no Bearer prefix).

Usage:
  VETSPIRE_API_TOKEN="..." python3 nightly_revenue_sync.py
"""

import json, urllib.request, urllib.error, os, sys
from datetime import date, timedelta, datetime, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "Lincoln Park": "23083",
    "Old Orchard":  "27390",
    "West Loop":    "24356",
    "Wheaton":      "28253",
}

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e)
}
"""

def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,   # API key — no Bearer prefix (same as lot sync)
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:200]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}
    except Exception as e:
        print(f"  Vetspire request failed: {e}")
        return {"errors": [{"message": str(e)}]}

def supa_upsert(records):
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
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code}: {e.read().decode()[:200]}")
        return e.code

# Field resolution — None-safe. Priority: paid > paidTotal > paidRevenue > collected > total.
# `total` includes open invoices but is used as last resort when the API token only returns it.
_PAID_FIELDS = ("paid", "paidTotal", "paidRevenue", "collected", "total")

def _paid_field(rec):
    """Return the name of the first paid-specific field present in rec, or 'none'."""
    for f in _PAID_FIELDS:
        if rec.get(f) is not None:
            return f
    return "none"

def _pick_paid(rec):
    """Return the value of the first paid-specific field, or 0.0 if none found."""
    for f in _PAID_FIELDS:
        val = rec.get(f)
        if val is not None:
            return float(val)
    return 0.0


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        # Fall back to token file for local runs
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip().removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    # Pull yesterday AND today so every run is current up to the moment it runs
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today     = date.today().isoformat()
    dates_to_pull = [yesterday, today]
    print(f"\n=== Revenue Sync — pulling {yesterday} + {today} ===")

    records = []
    _fields_logged = False
    for target_date in dates_to_pull:
        for loc_name, loc_id in LOCATIONS.items():
            print(f"  {loc_name} ({loc_id}) {target_date}...", end=" ", flush=True)
            result = gql(token, SALES_QUERY, {"lids": [loc_id], "s": target_date, "e": target_date})
            if "errors" in result:
                print(f"ERROR: {result['errors']}")
                continue
            raw = result.get("data", {}).get("salesReport", "[]")
            rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
            rec = rows[0] if rows else {}
            if not _fields_logged and rec:
                print(f"\n  [DEBUG] salesReport keys: {list(rec.keys())}")
                print(f"  [DEBUG] first record: {rec}")
                _fields_logged = True
            revenue = _pick_paid(rec)
            print(f"${revenue:,.2f}  (field: {_paid_field(rec)})")
            records.append({
                "date":          target_date,
                "location_id":   loc_id,
                "location_name": loc_name,
                "revenue":       revenue,
                "pulled_at":     datetime.now(timezone.utc).isoformat(),
            })

    if records:
        status = supa_upsert(records)
        print(f"\n  Supabase upsert → HTTP {status}")
    else:
        print("\n  No records to upsert.")

    print("Done.\n")

if __name__ == "__main__":
    main()
