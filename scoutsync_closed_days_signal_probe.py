#!/usr/bin/env python3
"""
Follow-up: for each location, find calendar days with ZERO encounters AND
ZERO revenue (the "neither" set -- days no signal shows any activity at
all), over the trailing 365 days, and characterize whether those days form
long consecutive runs (data-sync/backfill gap signature) or scattered
isolated days (closure signature, e.g. holidays). Also report the longest
consecutive run of "zero encounter" days regardless of revenue, since that
alone reveals whether the clinical sync itself has backfill gaps.
"""
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

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


def supa_get(table, query):
    url = f"{SUPA_URL}/rest/v1/{table}?{query}"
    req = urllib.request.Request(url, headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def supa_get_all(table, query, order_col):
    out, offset, page_size = [], 0, 1000
    while True:
        page = supa_get(table, f"{query}&order={order_col}.asc&limit={page_size}&offset={offset}")
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def local_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(
        __import__("zoneinfo").ZoneInfo("America/Chicago")
    ).date().isoformat()


def consecutive_runs(sorted_dates):
    """Given sorted YYYY-MM-DD strings, return list of (start, end, length) runs of consecutive calendar days."""
    if not sorted_dates:
        return []
    runs = []
    run_start = prev = sorted_dates[0]
    for d in sorted_dates[1:]:
        prev_dt = datetime.fromisoformat(prev)
        d_dt = datetime.fromisoformat(d)
        if (d_dt - prev_dt).days == 1:
            prev = d
            continue
        runs.append((run_start, prev, (datetime.fromisoformat(prev) - datetime.fromisoformat(run_start)).days + 1))
        run_start = prev = d
    runs.append((run_start, prev, (datetime.fromisoformat(prev) - datetime.fromisoformat(run_start)).days + 1))
    return runs


def main():
    since = (datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    rev_rows = supa_get_all(
        "v_avg_transaction_charge_daily",
        f"select=service_date,revenue,location_id&service_date=gte.{since}",
        "service_date",
    )
    enc_rows = supa_get_all(
        "encounters",
        f"select=location_id,started_at&started_at=gte.{since}&started_at=not.is.null",
        "started_at",
    )

    revenue_days = defaultdict(set)
    for r in rev_rows:
        if r.get("service_date") and r["service_date"] <= yesterday and float(r.get("revenue") or 0) > 0:
            revenue_days[r["location_id"]].add(r["service_date"])

    encounter_days = defaultdict(set)
    for e in enc_rows:
        if not e.get("started_at"):
            continue
        d = local_date(e["started_at"])
        if d <= yesterday:
            encounter_days[e["location_id"]].add(d)

    all_days = []
    d = datetime.fromisoformat(since)
    end = datetime.fromisoformat(yesterday)
    while d <= end:
        all_days.append(d.date().isoformat())
        d += timedelta(days=1)

    print(f"Window: {since} .. {yesterday} ({len(all_days)} calendar days)\n")
    for loc_id, name in LOCATIONS.items():
        edays = encounter_days[loc_id]
        rdays = revenue_days[loc_id]
        no_encounter_days = sorted(d for d in all_days if d not in edays)
        neither_days = sorted(d for d in all_days if d not in edays and d not in rdays)

        enc_runs = consecutive_runs(no_encounter_days)
        enc_runs_sorted = sorted(enc_runs, key=lambda r: -r[2])[:8]

        neither_runs = consecutive_runs(neither_days)
        neither_runs_sorted = sorted(neither_runs, key=lambda r: -r[2])[:8]

        print(f"=== {name} ===")
        print(f"  zero-ENCOUNTER days: {len(no_encounter_days)} / {len(all_days)}")
        print(f"  longest zero-encounter runs (start, end, length): {enc_runs_sorted}")
        print(f"  zero-encounter AND zero-revenue ('neither') days: {len(neither_days)} / {len(all_days)}")
        print(f"  longest 'neither' runs (start, end, length): {neither_runs_sorted}")
        print()


if __name__ == "__main__":
    main()
