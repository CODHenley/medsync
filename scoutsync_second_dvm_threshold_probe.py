#!/usr/bin/env python3
"""
scoutsync_second_dvm_threshold_probe.py
Investigates whether a single DVM regularly sees 12+ cases/day per location,
seriously enough to justify a second 1.0 FTE DVM there -- per the user's ask:
"I want to know definitively that a doctor is seeing 12+ cases regularly
enough to warrant a second DVM 1 FTE."

Method:
1. Pull all cases (encounters, had_exam=true) with provider_id/location_id/
   started_at, and all provider_shifts (actual Vetspire-scheduled staffing).
2. For each location+calendar day, compute how many DISTINCT providers
   actually saw a case that day (the real staffing signal -- provider_shifts
   is Vetspire's schedule, which can be incomplete/stale, so cross-check
   against who really worked, not just who was scheduled).
3. Restrict to single-provider days (exactly one DVM saw all of that day's
   cases) and look at that DVM's case count: what % of single-DVM days hit
   12+, what the weekly regularity looks like (not just isolated spikes),
   and how this breaks down per location.
4. Cross-reference two quality/strain proxies on single-DVM days, comparing
   <12-case days vs 12+-case days: (a) same-day reschedule rate (from
   appointment_events, reusing the isAffectedEvent/keptAppointmentDays logic
   already established on the dashboard) and (b) revenue per case (a proxy
   for whether a doctor is rushing/truncating visits under load).

Report-only. No writes.
"""
import json
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
}

THRESHOLD = 12


def get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.loads(r.read())
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def daterange(d1, d2):
    d = d1
    while d <= d2:
        yield d
        d += timedelta(days=1)


def main():
    print("=== Fetching cases (had_exam, all history) ===")
    encounters = get_all(
        "encounters",
        "select=id,location_id,provider_id,started_at"
        "&had_exam=eq.true&started_at=not.is.null&provider_id=not.is.null"
        "&order=started_at.asc,id.asc",
    )
    print(f"  {len(encounters)} cases with a provider on file\n")

    print("=== Fetching providers (for name lookup) ===")
    providers = get_all("providers", "select=id,full_name&order=id.asc")
    name_by_provider = {p["id"]: p.get("full_name") or p["id"][:8] for p in providers}
    print(f"  {len(providers)} providers\n")

    print("=== Fetching appointment_events (for same-day-reschedule check) ===")
    appts = get_all(
        "appointment_events",
        "select=location_id,scheduled_start,status,deleted,vetspire_patient_id"
        "&order=scheduled_start.asc,id.asc",
    )
    print(f"  {len(appts)} appointment events\n")

    # ── Step 1: cases per (location, day, provider) ──
    cases_by_loc_day_provider = defaultdict(lambda: defaultdict(int))
    for e in encounters:
        loc = e["location_id"]
        day = e["started_at"][:10]
        prov = e["provider_id"]
        cases_by_loc_day_provider[(loc, day)][prov] += 1

    # ── Step 2: restrict to single-provider days ──
    single_dvm_days = []  # (loc, day, provider, case_count)
    multi_dvm_days = 0
    for (loc, day), by_provider in cases_by_loc_day_provider.items():
        if len(by_provider) == 1:
            prov, count = next(iter(by_provider.items()))
            single_dvm_days.append((loc, day, prov, count))
        else:
            multi_dvm_days += 1

    total_days = len(cases_by_loc_day_provider)
    print(f"=== {total_days} location-days with at least one case ===")
    print(f"  {len(single_dvm_days)} single-DVM days ({100 * len(single_dvm_days) / total_days:.1f}%)")
    print(f"  {multi_dvm_days} multi-DVM days ({100 * multi_dvm_days / total_days:.1f}%)\n")

    # ── Step 3: per-location breakdown of single-DVM day case counts ──
    by_loc = defaultdict(list)
    for loc, day, prov, count in single_dvm_days:
        by_loc[loc].append((day, prov, count))

    print(f"=== Single-DVM day case-count distribution by location (threshold = {THRESHOLD}) ===\n")
    for loc_id, loc_name in LOCATIONS.items():
        rows = by_loc.get(loc_id, [])
        if not rows:
            print(f"{loc_name}: no single-DVM days found\n")
            continue
        counts = sorted(c for _, _, c in rows)
        n = len(counts)
        at_or_above = sum(1 for c in counts if c >= THRESHOLD)
        mean = sum(counts) / n
        median = counts[n // 2] if n % 2 else (counts[n // 2 - 1] + counts[n // 2]) / 2
        p90 = counts[int(n * 0.9)] if n > 1 else counts[0]
        print(f"{loc_name}: {n} single-DVM days")
        print(f"  mean {mean:.1f} · median {median:.1f} · p90 {p90} · max {counts[-1]}")
        print(f"  days at/above {THRESHOLD}: {at_or_above} ({100 * at_or_above / n:.1f}%)")

        # Regularity: how many distinct ISO weeks have >=1 single-DVM day at/above threshold,
        # vs total distinct ISO weeks with any single-DVM day at all -- isolated spikes vs a
        # recurring pattern look very different under this lens.
        weeks_with_single = defaultdict(list)
        for day, prov, count in rows:
            wk = date.fromisoformat(day).isocalendar()[:2]
            weeks_with_single[wk].append(count)
        weeks_total = len(weeks_with_single)
        weeks_hit = sum(1 for wk, cs in weeks_with_single.items() if max(cs) >= THRESHOLD)
        print(f"  weeks with >=1 single-DVM day: {weeks_total} · weeks where at least one hit {THRESHOLD}+: {weeks_hit} ({100 * weeks_hit / weeks_total:.1f}%)")

        # Per-provider: which specific DVM(s) are absorbing this at each location.
        by_provider_counts = defaultdict(list)
        for day, prov, count in rows:
            by_provider_counts[prov].append(count)
        for prov, cs in sorted(by_provider_counts.items(), key=lambda kv: -len(kv[1])):
            hit = sum(1 for c in cs if c >= THRESHOLD)
            print(f"    {name_by_provider.get(prov, prov)}: {len(cs)} single-DVM days, {hit} at/above {THRESHOLD} ({100 * hit / len(cs):.1f}%)")
        print()

    # ── Step 4: quality/strain proxy -- same-day reschedule rate ──
    # Reuse the dashboard's own isAffectedEvent/kept-appointment-same-day logic:
    # a cancelled/no-show/deleted appointment doesn't count as a real loss if
    # the same patient has another KEPT appointment at the same location the
    # same day (a reschedule, not a loss). Build kept-day index first.
    kept_days = set()  # (patient_id, location_id, date)
    for a in appts:
        if not a.get("vetspire_patient_id") or not a.get("scheduled_start"):
            continue
        status = a.get("status")
        if status in ("CANCELLED", "NOSHOW") or a.get("deleted"):
            continue
        kept_days.add((a["vetspire_patient_id"], a["location_id"], a["scheduled_start"][:10]))

    affected_by_loc_day = defaultdict(lambda: [0, 0])  # (loc, day) -> [affected_not_rescheduled, total]
    for a in appts:
        loc = a.get("location_id")
        sched = a.get("scheduled_start")
        if not loc or not sched:
            continue
        day = sched[:10]
        status = a.get("status")
        affected = status in ("CANCELLED", "NOSHOW") or bool(a.get("deleted"))
        key = (loc, day)
        affected_by_loc_day[key][1] += 1
        if affected:
            pid = a.get("vetspire_patient_id")
            rescheduled = pid and (pid, loc, day) in kept_days
            if not rescheduled:
                affected_by_loc_day[key][0] += 1

    print("=== Same-day loss rate on single-DVM days: <12 cases vs 12+ cases ===")
    under, over = [], []
    for loc, day, prov, count in single_dvm_days:
        stats = affected_by_loc_day.get((loc, day))
        if not stats or stats[1] == 0:
            continue
        rate = stats[0] / stats[1]
        (under if count < THRESHOLD else over).append(rate)
    if under and over:
        print(f"  <{THRESHOLD} cases: {len(under)} days, avg loss rate {100 * sum(under) / len(under):.1f}%")
        print(f"  {THRESHOLD}+ cases: {len(over)} days, avg loss rate {100 * sum(over) / len(over):.1f}%")
    else:
        print("  Not enough data on one side to compare.")
    print()

    print("=== Sample of 15 heaviest single-DVM days (any location) ===")
    heaviest = sorted(single_dvm_days, key=lambda x: -x[3])[:15]
    for loc, day, prov, count in heaviest:
        print(f"  {LOCATIONS.get(loc, loc)} · {day} · {name_by_provider.get(prov, prov)} · {count} cases")


if __name__ == "__main__":
    main()
