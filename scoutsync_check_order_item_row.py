#!/usr/bin/env python3
"""
scoutsync_check_order_item_row.py
Round 3 diagnostic (part 3): we just confirmed Vetspire's usageReport
returns product 523783 ("Exam - Urgent Care") correctly categorized as
"Service" for order_item_id 4182098114 (Aug 20-22, 2026 window, Lincoln
Park) -- the very field dispensed_items_backfill.py writes from. Does
that exact row exist in Supabase's dispensed_items, and if so, what does
it actually have stored for product_category_id?

If the row EXISTS with product_category_id=null -> the backfill fetched
correct data but failed to persist it (an upsert/write bug).
If the row is MISSING entirely -> Vetspire's usageReport response is
being truncated/dropped before ever reaching Supabase (a fetch/pagination
bug), and this specific null row must come from an older/different
writer.

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

ORDER_ITEM_IDS = [
    "4182098114", "4182104636", "4182112298", "4182129525", "4182148183",
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
            f"select=order_item_id,location_id,location_name,product_name,product_category_id,pulled_at,dispensed_at&order_item_id=eq.{oid}",
        )
        print(f"order_item_id={oid}: {len(rows)} row(s)")
        for r in rows:
            print(f"  {json.dumps(r)}")
        print()


if __name__ == "__main__":
    main()
