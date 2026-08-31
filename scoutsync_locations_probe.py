#!/usr/bin/env python3
"""One-off: check the `locations` table's open_date values and the earliest/
latest encounter dates per location, to scope a closed-days finance report."""
import json
import urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1t"
            "ZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0."
            "JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s")


def supa_get(table, query):
    url = f"{SUPA_URL}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    locs = supa_get("locations", "select=*")
    print("=== locations table ===")
    print(json.dumps(locs, indent=2))

    print("\n=== earliest/latest encounter per location ===")
    for loc in locs:
        loc_id = loc.get("id")
        earliest = supa_get("encounters", f"select=started_at&location_id=eq.{loc_id}&started_at=not.is.null&order=started_at.asc&limit=1")
        latest = supa_get("encounters", f"select=started_at&location_id=eq.{loc_id}&started_at=not.is.null&order=started_at.desc&limit=1")
        count = supa_get("encounters", f"select=id&location_id=eq.{loc_id}")
        print(f"{loc.get('name')}: open_date={loc.get('open_date')}, "
              f"earliest_encounter={earliest[0]['started_at'] if earliest else None}, "
              f"latest_encounter={latest[0]['started_at'] if latest else None}, "
              f"encounter_row_count(unpaginated head)={len(count)}")


if __name__ == "__main__":
    main()
