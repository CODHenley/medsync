#!/usr/bin/env python3
"""
scoutsync_round3_fragmentation_check.py
Round 3 diagnostic: the round 3 probe showed "Exam - Urgent Care" back at
the TOP of the uncategorized list at $1,188,805.98 all-time, despite being
one of the first items fixed in round 1. That's suspicious -- either the
round 1 fix didn't stick, or (more likely) there are multiple distinct
Vetspire product IDs sharing this same display name (e.g. one per
location) and round 1 only touched one of them.

For the top 15 uncategorized names by revenue, break down by DISTINCT
product_id to see how many separate Vetspire products share each name,
and how many of those distinct ids are still uncategorized.

Read-only. Deleted once its purpose is served, per this repo's convention.
"""
import json, urllib.parse, urllib.request
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

NAMES_TO_CHECK = [
    "Exam - Urgent Care",
    "Fluid Set-Up & Admin - SQ",
    "Maropitant Inj 10 mg/ml",
    "Exam - Recheck",
    "Catalyst NSAID 6",
    "Injection - IV/IM Administration",
    "Catalyst Pancreatic Lipase  (PL)",
    "Methadone Inj 10 mg/ml",
    "Cytology - Ear",
    "Gabapentin Solu 100 mg/ml",
    "Cremation - Private ",
    "Radiology - Addl View (Body System)",
    "Fecal Ova and Parasites with Giardia (2463)",
    "Wound Care - Clip/Clean/Flush ",
    "Proviable Paste Kit (Medium/Large Dog)",
]


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        page = supa_get(path, f"{params}&limit={page_size}&offset={offset}")
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def main():
    print("=== Round 3 diagnostic: product_id fragmentation for top uncategorized names ===\n")
    for name in NAMES_TO_CHECK:
        q = urllib.parse.quote(name)
        uncategorized_rows = supa_get_all(
            "dispensed_items",
            f"select=product_id,dispensed_at&product_category_id=is.null&product_name=eq.{q}",
        )
        all_rows = supa_get_all(
            "dispensed_items",
            f"select=product_id&product_name=eq.{q}",
        )
        uncategorized_ids = defaultdict(int)
        for r in uncategorized_rows:
            uncategorized_ids[r.get("product_id")] += 1
        all_ids = set(r.get("product_id") for r in all_rows)
        latest = max((r.get("dispensed_at") for r in uncategorized_rows), default=None)
        print(f"'{name}':")
        print(f"  total distinct product_ids (any category state): {len(all_ids)}")
        print(f"  distinct product_ids still UNCATEGORIZED: {len(uncategorized_ids)}")
        for pid, cnt in sorted(uncategorized_ids.items(), key=lambda kv: -kv[1]):
            print(f"    product_id={pid}: {cnt} uncategorized rows")
        print(f"  most recent uncategorized dispensed_at: {latest}")
        print()


if __name__ == "__main__":
    main()
