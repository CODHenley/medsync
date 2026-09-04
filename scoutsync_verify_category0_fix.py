#!/usr/bin/env python3
"""
scoutsync_verify_category0_fix.py
Verify the full-history (2023-01-01 to today) dispensed_items_backfill run
(193,533 rows upserted, 0 errors) actually fixed the category-0 backlog.
Checks the overall uncategorized total (all-time, all products) and
"Exam - Urgent Care" specifically (was 8833 before this backfill).

Read-only. Deleted once its purpose is served, per this repo's convention.
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def count_exact(params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/dispensed_items?{params}&limit=1",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Prefer": "count=exact"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        cr = r.headers.get("Content-Range", "")
    return cr.split("/")[-1] if "/" in cr else cr


def main():
    total_all = count_exact("select=id&product_category_id=is.null")
    print(f"Total uncategorized rows (all-time, all products): {total_all}")

    exam_urgent = count_exact("select=id&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null")
    print(f"'Exam - Urgent Care' uncategorized (was 8833 before this backfill): {exam_urgent}")

    total_rows = count_exact("select=id")
    print(f"\nTotal dispensed_items rows (all-time): {total_rows}")


if __name__ == "__main__":
    main()
