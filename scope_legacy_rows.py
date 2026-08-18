#!/usr/bin/env python3
"""
scope_legacy_rows.py
Read-only. Table-wide scan of dispensed_items to find the full extent of
legacy order_item_id IS NULL rows (day/month-aggregated writes from before
the order_item_id-as-sole-key fix), so a full remediation backfill+cleanup
can be scoped to the exact date range and locations that need it, instead
of guessing.
"""
import json, urllib.request
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "23083": "Lincoln Park",
    "27390": "Old Orchard",
    "24356": "West Loop",
    "28253": "Wheaton",
}


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}",
            headers={
                "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                "Range": f"{offset}-{offset + page_size - 1}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            chunk = json.loads(r.read())
        out.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return out


def main():
    print("=== Fetching ALL dispensed_items rows with order_item_id IS NULL ===")
    rows = supa_get_all(
        "dispensed_items",
        "select=location_id,dispensed_at,quantity,pulled_at&order_item_id=is.null&order=dispensed_at.asc",
    )
    print(f"  {len(rows)} legacy (order_item_id IS NULL) rows total\n")

    if not rows:
        print("No legacy rows found — table is fully per-item. Nothing to remediate.")
        return

    dispensed_ats = [r.get("dispensed_at") for r in rows if r.get("dispensed_at")]
    pulled_ats = [r.get("pulled_at") for r in rows if r.get("pulled_at")]
    print(f"dispensed_at range: {min(dispensed_ats)} .. {max(dispensed_ats)}")
    print(f"pulled_at range:    {min(pulled_ats)} .. {max(pulled_ats)}\n")

    by_loc = defaultdict(lambda: {"count": 0, "qty": 0.0, "dates": set()})
    for r in rows:
        loc = LOCATIONS.get(r.get("location_id"), r.get("location_id"))
        by_loc[loc]["count"] += 1
        by_loc[loc]["qty"] += float(r.get("quantity") or 0)
        by_loc[loc]["dates"].add((r.get("dispensed_at") or "")[:10])

    print("By location:")
    for loc, d in sorted(by_loc.items()):
        dates_sorted = sorted(d["dates"])
        print(f"  {loc:15s}  {d['count']:5d} rows   qty={d['qty']:10.1f}   "
              f"{len(dates_sorted)} distinct dates  ({dates_sorted[0]} .. {dates_sorted[-1]})")

    by_pulled_day = defaultdict(int)
    for r in rows:
        by_pulled_day[(r.get("pulled_at") or "")[:10]] += 1
    print("\nBy pulled_at day (when the legacy row was actually written):")
    for day, count in sorted(by_pulled_day.items()):
        print(f"  {day}: {count} rows")


if __name__ == "__main__":
    main()
