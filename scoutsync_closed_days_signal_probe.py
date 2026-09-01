#!/usr/bin/env python3
"""
One-off: compare two possible signals for "was this location closed on this
day" over the trailing 365 days, per location --
  (a) zero billed revenue that day (v_avg_transaction_charge_daily, what the
      shipped Days Closed report currently uses)
  (b) zero clinical encounters that day (encounters.started_at)
-- to find out which one actually matches what the user knows to be true
(closures/partial closures at Lincoln Park, Old Orchard, and West Loop that
the revenue-based signal isn't catching, apparently).
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
    # matches the dashboard's own Central-time convention
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(
        __import__("zoneinfo").ZoneInfo("America/Chicago")
    ).date().isoformat()


def main():
    since = (datetime.now(timezone.utc).date() - timedelta(days=365)).isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    rev_rows = supa_get_all(
        "v_avg_transaction_charge_daily",
        f"select=service_date,revenue,encounter_count,location_id&service_date=gte.{since}",
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
    enc_count_by_day = defaultdict(int)
    for e in enc_rows:
        if not e.get("started_at"):
            continue
        d = local_date(e["started_at"])
        if d <= yesterday:
            encounter_days[e["location_id"]].add(d)
            enc_count_by_day[(e["location_id"], d)] += 1

    print(f"Window: {since} .. {yesterday} (trailing 365 days, Central-time calendar days)\n")
    for loc_id, name in LOCATIONS.items():
        rdays = revenue_days[loc_id]
        edays = encounter_days[loc_id]
        rev_only = sorted(rdays - edays)          # revenue posted, but no encounter that day
        enc_only = sorted(edays - rdays)          # encounter happened, but no revenue posted that day
        neither = None  # computed below against full calendar range once we know first-activity date

        print(f"=== {name} ===")
        print(f"  distinct days with revenue>0:   {len(rdays)}")
        print(f"  distinct days with an encounter: {len(edays)}")
        print(f"  days with revenue but NO encounter that day ({len(rev_only)}): {rev_only[:15]}{' ...' if len(rev_only) > 15 else ''}")
        print(f"  days with an encounter but NO revenue that day ({len(enc_only)}): {enc_only[:15]}{' ...' if len(enc_only) > 15 else ''}")

        # low-volume "partial closure" candidates: encounter days with unusually
        # low visit counts vs. that location's own trailing median
        counts = sorted(enc_count_by_day[(loc_id, d)] for d in edays)
        if counts:
            median = counts[len(counts) // 2]
            low_days = sorted(d for d in edays if enc_count_by_day[(loc_id, d)] > 0
                               and enc_count_by_day[(loc_id, d)] <= max(1, median * 0.25))
            print(f"  median encounters/open-day: {median}; low-volume candidate days (<=25% of median, {len(low_days)}): {low_days[:15]}{' ...' if len(low_days) > 15 else ''}")
        print()


if __name__ == "__main__":
    main()
