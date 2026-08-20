#!/usr/bin/env python3
"""
diagnose_portfolio_cogs_limit.py
Read-only. Checks whether the Portfolio/Analytics dispensed_items queries
that back the Drug COGS figures are hitting their hardcoded `limit=5000`
row cap for the current month-to-date window — which would silently
truncate results with no pagination and no error, understating spend.

Reports, for the trailing MTD window used by both screens:
  - exact row count per location (Analytics' per-location query shape)
  - exact row count for all 4 locations combined in one filter
    (Portfolio's loadLiveCOGs/loadLocationCards query shape)
  - whether either exceeds limit=5000
"""
import json, os, sys, urllib.request
from datetime import date, timedelta

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = [
    {"id": "23083", "name": "Lincoln Park"},
    {"id": "27390", "name": "Old Orchard"},
    {"id": "24356", "name": "West Loop"},
    {"id": "28253", "name": "Wheaton"},
]


def exact_count(params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/dispensed_items?{params}",
        headers={
            "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        cr = r.getheader("Content-Range")  # e.g. "0-0/12345"
        r.read()
    return int(cr.split("/")[1]) if cr and "/" in cr else None


def main():
    end = date.today()
    start = date(end.year, end.month, 1)
    print(f"=== MTD window: {start} to {end} ===\n")

    total_all = 0
    for loc in LOCATIONS:
        n = exact_count(
            f"select=id&location_id=eq.{loc['id']}"
            f"&dispensed_at=gte.{start}T00:00:00&dispensed_at=lte.{end}T23:59:59"
        )
        total_all += n or 0
        flag = "  <-- EXCEEDS limit=5000, would be silently truncated" if n and n > 5000 else ""
        print(f"  {loc['name']:12s}: {n} rows{flag}")

    combined_ids = ",".join(l["id"] for l in LOCATIONS)
    n_combined = exact_count(
        f"select=id&location_id=in.({combined_ids})"
        f"&dispensed_at=gte.{start}T00:00:00&dispensed_at=lte.{end}T23:59:59"
    )
    print(f"\n  Combined (all 4, single filter): {n_combined} rows"
          f"{'  <-- EXCEEDS limit=5000, would be silently truncated' if n_combined and n_combined > 5000 else ''}")
    print(f"  Sum of per-location counts:      {total_all}")

    if n_combined != total_all:
        print(f"\n  MISMATCH between combined count and sum of per-location counts ({n_combined} vs {total_all})")


if __name__ == "__main__":
    main()
