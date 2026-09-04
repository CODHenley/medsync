#!/usr/bin/env python3
"""
scoutsync_probe_chief_complaint.py
Investigating a new "invoicing variance by doctor, same illness" feature
for the Clinical Operations tab. encounters.chief_complaint is the closest
proxy we have to "illness" (real diagnosis data isn't synced). Before
designing any normalization/bucketing, sample the actual distinct values
and their frequency -- free text fields are unpredictable, and guessing
buckets without seeing real data would likely miss how doctors actually
write these.

Read-only. Deleted once its purpose is served, per this repo's convention.
"""
import json, urllib.request
from collections import Counter

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.loads(r.read())
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def main():
    print("=== Sampling encounters.chief_complaint (trailing 180 days) ===\n")
    rows = supa_get_all(
        "encounters",
        "select=chief_complaint&started_at=gte.2026-03-01&chief_complaint=not.is.null",
    )
    print(f"Total non-null chief_complaint rows in window: {len(rows)}\n")

    raw_counts = Counter((r.get("chief_complaint") or "").strip() for r in rows)
    print(f"-- {len(raw_counts)} distinct RAW values --")
    print("Top 60 by frequency:")
    for val, cnt in raw_counts.most_common(60):
        print(f"  {cnt:>5}x  {val!r}")

    print("\n-- Same values lowercased, for a rough sense of case-variant duplication --")
    lower_counts = Counter((r.get("chief_complaint") or "").strip().lower() for r in rows)
    print(f"{len(lower_counts)} distinct lowercased values (vs {len(raw_counts)} raw)")

    empty = sum(1 for r in rows if not (r.get("chief_complaint") or "").strip())
    print(f"\nBlank/whitespace-only chief_complaint (after not.is.null filter): {empty}")


if __name__ == "__main__":
    main()
