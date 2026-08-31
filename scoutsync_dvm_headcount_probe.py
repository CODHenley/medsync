#!/usr/bin/env python3
"""
One-off: current active DVM headcount by location, for the paraprofessional
staffing-ratio analysis.

"Active" = has at least one encounter with started_at on/after ACTIVE_SINCE
(default 2026-07-01) -- providers who only show up in older history (e.g.
departed doctors) are excluded even if they're still sitting in the
`providers` dimension table. Departed-by-name is also applied explicitly
(Simpson, Hill) as a safety net in case their last encounter happens to
fall inside the active window during a transition period.

Uses the same public anon key already embedded client-side in
scoutsync_dashboard.html -- read-only, RLS-scoped, no secret required.
"""
import argparse
import json
import urllib.request
import urllib.parse
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1t"
            "ZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0."
            "JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s")

LOCATIONS = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}

DEPARTED_NAME_SUBSTRINGS = ["simpson", "hill"]


def supa_get(table, query):
    url = f"{SUPA_URL}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--active-since", default="2026-07-01")
    args = ap.parse_args()

    providers = supa_get("providers", "select=id,full_name,location_id")
    name_by_id = {p["id"]: (p.get("full_name") or "Unnamed") for p in providers}

    encounters = supa_get(
        "encounters",
        f"select=provider_id,location_id,started_at&started_at=gte.{args.active_since}"
        "&provider_id=not.is.null&limit=50000",
    )

    active_by_location = defaultdict(set)
    for e in encounters:
        pid, loc = e.get("provider_id"), e.get("location_id")
        if not pid or not loc:
            continue
        active_by_location[loc].add(pid)

    print(f"Active-since cutoff: {args.active_since}")
    print(f"Total providers in dimension table: {len(providers)}")
    print(f"Total encounters scanned: {len(encounters)}\n")

    grand_total = 0
    for loc_uuid, loc_name in LOCATIONS.items():
        pids = active_by_location.get(loc_uuid, set())
        names = []
        for pid in pids:
            name = name_by_id.get(pid, "Unknown")
            if any(sub in name.lower() for sub in DEPARTED_NAME_SUBSTRINGS):
                print(f"  [excluded departed] {name} ({loc_name})")
                continue
            names.append(name)
        names.sort()
        grand_total += len(names)
        print(f"=== {loc_name}: {len(names)} active DVM(s) ===")
        for n in names:
            print(f"  - {n}")
        print()

    print(f"TOTAL ACTIVE DVM FTEs ACROSS ALL LOCATIONS: {grand_total}")


if __name__ == "__main__":
    main()
