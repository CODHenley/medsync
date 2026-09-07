#!/usr/bin/env python3
"""
scoutsync_heatmap_crosscheck.py
Cross-checks ScoutSync's v_case_heatmap against an independently-pulled
coworker spreadsheet of raw Vetspire appointment counts (Jan 1 - Sep 3,
2026, all 4 locations) -- see uploaded Scout_Appointment_Heatmaps.xlsx.

v_case_heatmap computes day_of_week/hour_of_day via extract(dow/hour from
e.started_at) directly on a timestamptz column, with NO explicit
`at time zone 'America/Chicago'` conversion -- unlike v_case_volume_monthly,
which does convert. Postgres's extract() on a timestamptz uses the
connection's session timezone (UTC by default on Supabase), so this may be
silently bucketing every case's hour (and sometimes day) by UTC instead of
real local clinic time. This pulls v_case_heatmap's raw started_at values
and recomputes both ways client-side to test that directly, then compares
both against the spreadsheet's grids.

Report-only. No writes.

Usage:
  python3 scoutsync_heatmap_crosscheck.py
"""
import json, urllib.request
from datetime import datetime, timezone, timedelta

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Central Time offset from UTC. Not using a full tz database here -- just
# testing the specific hypothesis (fixed CDT -5 for this date range, which
# covers Jan-Sep 2026; DST in the US runs roughly mid-March to early
# November, so CST (-6) applies to the small Jan 1 - Mar 8 sliver and CDT
# (-5) to the rest). Good enough to test the hypothesis; a real fix should
# use a proper tz conversion in SQL, not this approximation.
def to_central(dt_utc):
    # 2026 DST: second Sunday in March (Mar 8) to first Sunday in November.
    dst_start = datetime(2026, 3, 8, 8, tzinfo=timezone.utc)  # 2am CST = 8am UTC
    is_dst = dt_utc >= dst_start
    offset = timedelta(hours=-5) if is_dst else timedelta(hours=-6)
    return dt_utc + offset


def get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.loads(r.read())
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def hour_label(h):
    if h == 0:
        return "12 AM"
    if h < 12:
        return f"{h} AM"
    if h == 12:
        return "12 PM"
    return f"{h - 12} PM"


def main():
    print("=== Fetching v_case_heatmap rows (Jan 1 - Sep 3, 2026) ===")
    rows = get_all(
        "v_case_heatmap",
        "select=location_id,started_at,day_of_week,hour_of_day"
        "&started_at=gte.2026-01-01T00:00:00&started_at=lt.2026-09-04T00:00:00",
    )
    print(f"  {len(rows)} total case rows fetched\n")

    # Grid keyed by (location_id, computed_weekday_name, hour) -> count, for
    # both the RAW view columns (as stored) and a Python Central-time
    # recomputation from the same started_at values.
    raw_grid = {}
    central_grid = {}
    raw_total = 0
    central_total = 0

    for r in rows:
        loc = r.get("location_id")
        started_at = r.get("started_at")
        if not started_at:
            continue
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))

        # As the view currently returns it (Postgres session-timezone extract).
        raw_dow = r.get("day_of_week")  # 0=Sunday..6=Saturday (Postgres convention)
        raw_hour = r.get("hour_of_day")
        if raw_dow is not None and raw_hour is not None:
            raw_weekday_name = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][raw_dow]
            key = (loc, raw_weekday_name, raw_hour)
            raw_grid[key] = raw_grid.get(key, 0) + 1
            raw_total += 1

        # Recomputed in real America/Chicago local time from the same instant.
        dt_central = to_central(dt)
        central_weekday_name = WEEKDAY_NAMES[dt_central.weekday()]
        key = (loc, central_weekday_name, dt_central.hour)
        central_grid[key] = central_grid.get(key, 0) + 1
        central_total += 1

    print(f"Raw view total: {raw_total}, Central-recomputed total: {central_total}\n")

    for loc_id, loc_name in LOCATIONS.items():
        print(f"=== {loc_name} ===")
        print("Full 24h distribution -- raw view vs. Central-recomputed (all days combined):")
        for h in range(24):
            raw_h = sum(v for (l, d, hh), v in raw_grid.items() if l == loc_id and hh == h)
            cen_h = sum(v for (l, d, hh), v in central_grid.items() if l == loc_id and hh == h)
            marker = "  <-- spreadsheet range" if 9 <= h <= 21 else ""
            print(f"  {hour_label(h):<6} | raw={raw_h:<5} | central={cen_h:<5}{marker}")
        raw_loc_total = sum(v for (l, d, hh), v in raw_grid.items() if l == loc_id)
        cen_loc_total = sum(v for (l, d, hh), v in central_grid.items() if l == loc_id)
        raw_in_range = sum(v for (l, d, hh), v in raw_grid.items() if l == loc_id and 9 <= hh <= 21)
        cen_in_range = sum(v for (l, d, hh), v in central_grid.items() if l == loc_id and 9 <= hh <= 21)
        print(f"  TOTAL (all 24h, raw view)             : {raw_loc_total}")
        print(f"  TOTAL (all 24h, Central-recomputed)   : {cen_loc_total}")
        print(f"  TOTAL (9AM-9PM only, raw view)         : {raw_in_range}")
        print(f"  TOTAL (9AM-9PM only, Central-recomputed): {cen_in_range}")
        print()
        print("  Central-recomputed grid, 9AM-9PM (Mon Tue Wed Thu Fri Sat Sun):")
        for h in range(9, 22):
            counts = [central_grid.get((loc_id, wd, h), 0) for wd in WEEKDAY_NAMES]
            print(f"    {hour_label(h):<6} {counts}")
        print()


if __name__ == "__main__":
    main()
