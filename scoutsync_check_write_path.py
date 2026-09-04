#!/usr/bin/env python3
"""
scoutsync_check_write_path.py
The read side is now fully cleared: replaying dispensed_items_backfill.py's
EXACT query shape (full calendar month, one location) for August 2026 @
Lincoln Park returned all 347 "Exam - Urgent Care" order items, every one
correctly categorized "Service" -- no truncation, no stale category.

A fresh full-history backfill ran at ~15:42-15:47 UTC today (after this
data was confirmed correct), yet "Exam - Urgent Care"'s uncategorized
count barely moved. Check the ACTUAL current Supabase state of specific
order items from that August response (including several from well
within the last 21 days, which intraday sync normally keeps fresh) to
see whether the backfill's WRITE actually persisted the category it
fetched, or silently no-op'd.

Read-only (Supabase only). Deleted once its purpose is served, per this
repo's convention.
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# From the month-truncation check's sample: all confirmed live-correct
# ("Service") in Vetspire via the exact query the backfill uses.
ORDER_ITEM_IDS = [
    "4169537301",  # Aug 1  -- outside intraday's 21-day window as of Sept 4
    "4176499298",  # Aug 16 -- inside intraday's 21-day window as of Sept 4
    "4176503323",  # Aug 16 -- inside
    "4176505635",  # Aug 16 -- inside
    "4176506744",  # Aug 16 -- inside
]


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    for oid in ORDER_ITEM_IDS:
        rows = supa_get(
            "dispensed_items",
            f"select=order_item_id,location_id,product_name,product_category_id,pulled_at,dispensed_at&order_item_id=eq.{oid}",
        )
        print(f"order_item_id={oid}: {len(rows)} row(s)")
        for r in rows:
            print(f"  {json.dumps(r)}")
        print()


if __name__ == "__main__":
    main()
