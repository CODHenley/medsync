#!/usr/bin/env python3
"""One-off: check exactly what provider_shifts, v_avg_transaction_charge_daily,
and encounters show for 2025-10-17 at each of the 4 locations -- user says
this was a real no-patient day at one location and it's not showing as
closed in the Days Closed report."""
import json
import urllib.request

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

DATE = "2025-10-17"


def supa_get(table, query):
    url = f"{SUPA_URL}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    print(f"=== {DATE} (a Friday) across all 4 locations ===\n")

    shifts = supa_get("provider_shifts", f"select=location_id,provider_id,shift_start,shift_end,vetspire_shift_id&shift_start=lte.{DATE}&shift_end=gte.{DATE}")
    revenue = supa_get("v_avg_transaction_charge_daily", f"select=location_id,revenue,encounter_count&service_date=eq.{DATE}")
    encounters = supa_get("encounters", f"select=location_id,id,started_at,had_exam&started_at=gte.{DATE}T00:00:00&started_at=lt.{DATE}T23:59:59.999")
    providers = supa_get("providers", "select=id,full_name")
    name_by_id = {p["id"]: p["full_name"] for p in providers}

    for loc_id, loc_name in LOCATIONS.items():
        loc_shifts = [s for s in shifts if s["location_id"] == loc_id]
        loc_rev = [r for r in revenue if r["location_id"] == loc_id]
        loc_enc = [e for e in encounters if e["location_id"] == loc_id]
        print(f"--- {loc_name} ---")
        print(f"  provider_shifts rows covering {DATE}: {len(loc_shifts)}")
        for s in loc_shifts:
            print(f"    shift_id={s['vetspire_shift_id']} provider={name_by_id.get(s['provider_id'], s['provider_id'])} start={s['shift_start']} end={s['shift_end']}")
        print(f"  v_avg_transaction_charge_daily rows: {loc_rev}")
        print(f"  encounters that day: {len(loc_enc)}")
        for e in loc_enc:
            print(f"    id={e['id']} started_at={e['started_at']} had_exam={e['had_exam']}")
        print()


if __name__ == "__main__":
    main()
