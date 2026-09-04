#!/usr/bin/env python3
"""
scoutsync_recheck_exam_urgent_care.py
The round 3 probe (15:48 UTC) showed "Exam - Urgent Care" essentially
unchanged (8834 -> 8833 rows) right after a full-history backfill
completed (15:47 UTC) that reported 0 errors and successfully upserted
2832/3185 August items alone (the 353 gap is items with no product id at
all, unrelated to this product). Direct spot-checks at 16:48 UTC show
several of those exact August order items -- including one whose
pulled_at timestamp (15:44:25) falls DURING that same backfill run --
are now correctly categorized "Service" in Supabase.

This gets the current live count for "Exam - Urgent Care" specifically,
over an hour after the backfill, to see whether it actually dropped
substantially (meaning the round-3 probe's reading was just stale/
transient) or is still stuck near 8833 (meaning something else is
wrong).

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Prefer": "count=exact"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        content_range = r.headers.get("Content-Range", "")
        return json.loads(r.read()), content_range


def main():
    rows, cr = supa_get(
        "dispensed_items",
        "select=order_item_id&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null&limit=1",
    )
    print(f"Current live count of uncategorized 'Exam - Urgent Care' rows: Content-Range={cr}")

    # Also break down by month to see WHICH months (if any) are still stuck.
    for start, end, label in [
        ("2026-01-01", "2026-01-31", "Jan"), ("2026-02-01", "2026-02-28", "Feb"),
        ("2026-03-01", "2026-03-31", "Mar"), ("2026-04-01", "2026-04-30", "Apr"),
        ("2026-05-01", "2026-05-31", "May"), ("2026-06-01", "2026-06-30", "Jun"),
        ("2026-07-01", "2026-07-31", "Jul"), ("2026-08-01", "2026-08-31", "Aug"),
        ("2026-09-01", "2026-09-04", "Sep"),
    ]:
        _, cr = supa_get(
            "dispensed_items",
            f"select=order_item_id&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null"
            f"&dispensed_at=gte.{start}&dispensed_at=lte.{end}T23:59:59&limit=1",
        )
        print(f"  {label} 2026: Content-Range={cr}")


if __name__ == "__main__":
    main()
