#!/usr/bin/env python3
"""
MedSync — Revenue Backfill
Pulls daily revenue from Vetspire salesReport for all 4 Scout locations
and upserts to Supabase daily_revenue table.

Can be triggered manually or via GitHub Actions workflow_dispatch.

Usage:
  python3 all_locations_revenue_backfill.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--location NAME] [--days N]
  VETSPIRE_API_TOKEN="..." python3 all_locations_revenue_backfill.py --start 2026-06-01 --end 2026-06-26

Defaults to last 90 days for all locations if no args given.
"""

import argparse, json, urllib.request, urllib.error, os
from datetime import date, datetime, timezone, timedelta

VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
DEFAULT_DAYS      = 90

ALL_LOCATIONS = [
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

# Paid-only field resolution — None-safe, never touches `total` (includes open invoices).
# Priority: paid > paidTotal > paidRevenue > collected (finalized = paid + due).
_PAID_FIELDS = ("paid", "paidTotal", "paidRevenue", "collected")

def _pick_paid(rec):
    for f in _PAID_FIELDS:
        val = rec.get(f)
        if val is not None:
            return float(val), f
    return 0.0, "none"


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if token:
        return token.removeprefix("Bearer ").strip()
    for path in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetspire_token.txt"),
        os.path.expanduser("~/.vetspire_token"),
    ):
        if os.path.exists(path):
            return open(path).read().strip().removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set and no token file found.")


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
        "Origin":        "https://scoutcare.vetspire.com",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:200]}"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


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


def run(token, start, end, locations):
    print(f"\n{'='*55}")
    print(f"  Revenue Backfill  |  {start} → {end}")
    print(f"  Locations: {', '.join(n for n, _ in locations)}")
    print(f"{'='*55}\n")

    grand_days = grand_revenue = 0
    _fields_logged = False

    for loc_name, loc_id in locations:
        print(f"── {loc_name} ({loc_id}) ──")
        loc_days = loc_revenue = 0
        cursor = start

        while cursor <= end:
            s = cursor.isoformat()
            r = gql(token, SALES_QUERY, {"lids": [loc_id], "s": s, "e": s})

            if "errors" in r:
                print(f"  {s}: ERROR — {r['errors'][0]['message'][:100]}")
                cursor += timedelta(days=1)
                continue

            raw     = r.get("data", {}).get("salesReport", "[]")
            rows    = json.loads(raw) if isinstance(raw, str) else (raw or [])
            rec     = rows[0] if rows else {}

            if not _fields_logged and rec:
                print(f"  [DEBUG] salesReport keys: {list(rec.keys())}")
                _fields_logged = True

            revenue, field_used = _pick_paid(rec)
            status = supa_upsert([{
                "date":          s,
                "location_id":   loc_id,
                "location_name": loc_name,
                "revenue":       revenue,
                "pulled_at":     datetime.now(timezone.utc).isoformat(),
            }])

            mark = "✓" if str(status).startswith("2") else f"✗ ({status})"
            print(f"  {s}  ${revenue:>10,.2f}  [{field_used}]  {mark}")
            if str(status).startswith("2"):
                loc_days += 1
                loc_revenue += revenue

            cursor += timedelta(days=1)

        avg = loc_revenue / max(loc_days, 1)
        print(f"  → {loc_days} days  ${loc_revenue:,.2f} total  ${avg:,.2f}/day avg\n")
        grand_days    += loc_days
        grand_revenue += loc_revenue

    print(f"{'='*55}")
    print(f"Complete!  {grand_days} days upserted  ${grand_revenue:,.2f} total revenue")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill daily revenue from Vetspire → Supabase")
    parser.add_argument("--start",    default=None, help="Start date YYYY-MM-DD (default: --days ago)")
    parser.add_argument("--end",      default=None, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--days",     type=int, default=DEFAULT_DAYS, help="Days back from end if --start omitted")
    parser.add_argument("--location", default=None, help="Single location name (default: all)")
    args = parser.parse_args()

    end   = date.fromisoformat(args.end)   if args.end   else date.today()
    start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days)

    locations = ALL_LOCATIONS
    if args.location:
        locations = [(n, i) for n, i in ALL_LOCATIONS if n.lower() == args.location.lower()]
        if not locations:
            raise SystemExit(f"ERROR: Unknown location '{args.location}'. Valid: {[n for n,_ in ALL_LOCATIONS]}")

    run(load_token(), start, end, locations)
