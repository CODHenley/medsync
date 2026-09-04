#!/usr/bin/env python3
"""
scoutsync_sample_null_dispensed_at.py
The exact count for "Exam - Urgent Care" uncategorized rows is 8833
(count=exact, no date filter), but summing per-month counts across the
ONLY months that could possibly exist (Jan-Sep 2026, since that's the
platform's data floor) only totals 19. ~8814 rows are unaccounted for --
scope_legacy_rows.py just confirmed there are 0 rows with order_item_id
IS NULL, ruling out that known legacy-row class.

Directly sample dispensed_at (and other fields) for a batch of these
"uncategorized, no date filter" rows to see where they actually fall --
NULL dispensed_at, a bad/out-of-range date, or something else entirely.

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, urllib.request
from collections import Counter

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    rows = supa_get(
        "dispensed_items",
        "select=order_item_id,vetspire_product_id,location_id,dispensed_at,pulled_at,product_category_id"
        "&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null&limit=30&order=id.asc",
    )
    print(f"-- First 30 rows (order by internal id) --")
    for r in rows:
        print(f"  {json.dumps(r)}")

    print(f"\n-- dispensed_at year distribution across a wider sample (limit=2000) --")
    rows2 = supa_get(
        "dispensed_items",
        "select=dispensed_at"
        "&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null&limit=2000&order=id.asc",
    )
    null_count = sum(1 for r in rows2 if r.get("dispensed_at") is None)
    years = Counter((r.get("dispensed_at") or "NULL")[:4] for r in rows2)
    print(f"  sample size: {len(rows2)}, NULL dispensed_at: {null_count}")
    for year, cnt in years.most_common(20):
        print(f"    {year}: {cnt}")

    print(f"\n-- vetspire_product_id distribution in that same sample --")
    pids = Counter(r.get("vetspire_product_id") for r in supa_get(
        "dispensed_items",
        "select=vetspire_product_id"
        "&product_name=eq.Exam%20-%20Urgent%20Care&product_category_id=is.null&limit=2000&order=id.asc",
    ))
    for pid, cnt in pids.most_common(10):
        print(f"    vetspire_product_id={pid}: {cnt}")


if __name__ == "__main__":
    main()
