#!/usr/bin/env python3
"""
scoutsync_nine_am_anomaly_probe.py
Digs into the one real anomaly the heatmap cross-check turned up: the 9 AM
hour bucket has MORE ScoutSync cases (286) than the coworker's raw
appointment count (167) -- the only hour running the wrong direction (every
other hour has ScoutSync running lower, as expected for a stricter
had_exam-only case definition vs. all booked appointments).

vetspire_clinical_sync.py sets started_at = enc.get("start") or
appt.get("startedAt") -- a fallback that only kicks in when Encounter.start
is missing. If either of these sometimes gets set to a scheduled/nominal
appointment time (e.g., snapped to a round hour) rather than a true
timestamped arrival event, cases would cluster at exact top-of-hour minute
values for the day's first slot -- worth checking directly against the
minute-level distribution before guessing further.

Report-only. No writes.

Usage:
  python3 scoutsync_nine_am_anomaly_probe.py
"""
import json, urllib.request
from datetime import datetime, timezone, timedelta
from collections import Counter

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}


def to_central(dt_utc):
    dst_start = datetime(2026, 3, 8, 8, tzinfo=timezone.utc)
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


def main():
    print("=== Fetching encounters (had_exam, Jan 1 - Sep 3, 2026) with checked_in_at ===")
    rows = get_all(
        "encounters",
        "select=id,location_id,started_at,checked_in_at,completed_at,visit_type"
        "&had_exam=eq.true&started_at=gte.2026-01-01T00:00:00&started_at=lt.2026-09-04T00:00:00",
    )
    print(f"  {len(rows)} total encounters fetched\n")

    nine_am_rows = []
    for r in rows:
        started_at = r.get("started_at")
        if not started_at:
            continue
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        dt_central = to_central(dt)
        if dt_central.hour == 9:
            nine_am_rows.append((r, dt_central))

    print(f"=== {len(nine_am_rows)} encounters land in the 9 AM Central-time bucket ===\n")

    minute_counter = Counter(dt.minute for _, dt in nine_am_rows)
    print("Minute-of-hour distribution within the 9 AM bucket (0-59):")
    for minute in sorted(minute_counter):
        print(f"  :{minute:02d} -- {minute_counter[minute]} encounters")
    print()

    exact_top_of_hour = sum(1 for _, dt in nine_am_rows if dt.minute == 0 and dt.second == 0)
    print(f"Exactly 9:00:00 (top of hour, zero seconds): {exact_top_of_hour} of {len(nine_am_rows)} "
          f"({100 * exact_top_of_hour / len(nine_am_rows):.1f}%)" if nine_am_rows else "N/A")
    print()

    print("=== Sample of up to 20 raw 9 AM rows (started_at, checked_in_at, signed_datetime, visit_type) ===")
    for r, dt_central in nine_am_rows[:20]:
        print(f"  loc={LOCATIONS.get(r.get('location_id'), r.get('location_id'))} "
              f"started_at={r.get('started_at')} (central {dt_central.strftime('%H:%M:%S')}) "
              f"checked_in_at={r.get('checked_in_at')} signed_datetime={r.get('signed_datetime')} "
              f"visit_type={r.get('visit_type')}")
    print()

    # Compare started_at vs checked_in_at directly for the 9 AM cohort --
    # a real arrival should have checked_in_at at or slightly before
    # started_at; a placeholder/default started_at would show a large or
    # nonsensical (e.g. negative, or checked_in_at completely absent while
    # everywhere else it's populated) gap.
    with_checkin = [(r, dt) for r, dt in nine_am_rows if r.get("checked_in_at")]
    without_checkin = len(nine_am_rows) - len(with_checkin)
    print(f"9 AM rows WITH a checked_in_at value: {len(with_checkin)}")
    print(f"9 AM rows WITHOUT a checked_in_at value (null): {without_checkin}")
    if nine_am_rows:
        pct_missing = 100 * without_checkin / len(nine_am_rows)
        print(f"  -> {pct_missing:.1f}% of 9 AM cases have no checked_in_at at all")

    # Same check for a comparable non-anomalous hour (10 AM) as a control.
    ten_am_rows = []
    for r in rows:
        started_at = r.get("started_at")
        if not started_at:
            continue
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        dt_central = to_central(dt)
        if dt_central.hour == 10:
            ten_am_rows.append((r, dt_central))
    ten_am_without_checkin = sum(1 for r, _ in ten_am_rows if not r.get("checked_in_at"))
    print(f"\nControl: 10 AM rows WITHOUT a checked_in_at value: {ten_am_without_checkin} of {len(ten_am_rows)}"
          + (f" ({100 * ten_am_without_checkin / len(ten_am_rows):.1f}%)" if ten_am_rows else ""))


if __name__ == "__main__":
    main()
