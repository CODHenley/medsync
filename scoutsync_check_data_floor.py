#!/usr/bin/env python3
"""
scoutsync_check_data_floor.py
User question: why does "Trailing 365 days" on the dashboard only show
about half a year of real data, across all locations?

Hypothesis: invoice_line_items (which drives the trend chart, hero tiles,
Revenue by Source, and Revenue per Veterinarian) simply doesn't have rows
going back a full 365 days -- the sync pipeline's own backfills
(vetspire_financial_sync.py, revenue_backfill.py) default to starting
2026-01-01, so if that's genuinely the earliest data ever captured, a
365-day trailing window (~Sept 2025 - Sept 2026) would show real data for
only the Jan-Sept portion (~8 months) and nothing before it -- which
would look like "half a year" missing, for every location, since it's a
platform-wide data floor rather than a per-location issue.

Checks the actual earliest invoice_line_items date (overall and per
location), plus dispensed_items for comparison.

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    print("=== Earliest invoice_line_items date (overall) ===")
    rows = supa_get("invoice_line_items", "select=service_date&order=service_date.asc&limit=5")
    for r in rows:
        print(f"  {r}")

    print("\n=== Earliest invoice_line_items date per location ===")
    locations = supa_get("locations", "select=id,name&limit=20")
    for loc in locations:
        rows = supa_get(
            "invoice_line_items",
            f"select=service_date&location_id=eq.{loc['id']}&order=service_date.asc&limit=1",
        )
        earliest = rows[0]["service_date"] if rows else "(no rows)"
        print(f"  {loc['name']}: earliest = {earliest}")

    print("\n=== Earliest dispensed_items date (overall), for comparison ===")
    rows = supa_get("dispensed_items", "select=dispensed_at&order=dispensed_at.asc&limit=5")
    for r in rows:
        print(f"  {r}")

    print("\n=== Row counts by month, invoice_line_items (overall) ===")
    for start, end, label in [
        ("2025-09-01", "2025-09-30", "Sep 2025"), ("2025-10-01", "2025-10-31", "Oct 2025"),
        ("2025-11-01", "2025-11-30", "Nov 2025"), ("2025-12-01", "2025-12-31", "Dec 2025"),
        ("2026-01-01", "2026-01-31", "Jan 2026"), ("2026-02-01", "2026-02-28", "Feb 2026"),
        ("2026-03-01", "2026-03-31", "Mar 2026"), ("2026-04-01", "2026-04-30", "Apr 2026"),
        ("2026-05-01", "2026-05-31", "May 2026"), ("2026-06-01", "2026-06-30", "Jun 2026"),
        ("2026-07-01", "2026-07-31", "Jul 2026"), ("2026-08-01", "2026-08-31", "Aug 2026"),
        ("2026-09-01", "2026-09-04", "Sep 2026 (partial)"),
    ]:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/invoice_line_items?select=id&service_date=gte.{start}&service_date=lte.{end}&limit=1",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Prefer": "count=exact"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            cr = r.headers.get("Content-Range", "")
        print(f"  {label}: Content-Range={cr}")


if __name__ == "__main__":
    main()
