#!/usr/bin/env python3
"""
scoutsync_uncategorized_round2_probe.py
Round 2: after the first batch of ~42 recommended categorizations was
applied and confirmed to work retroactively (Revenue by Source's
Uncategorized total dropped from $498,743 to $236,278 on the live
dashboard), what's left in the long tail?

Same shape as scoutsync_uncategorized_services_probe.py, but:
  - wider window (180 days instead of 90) to surface more of the tail
  - top 80 instead of top 40, since the biggest items are already handled
  - re-fetches product_categories fresh (in case new ones exist)

Read-only. Deleted once its purpose is served, per this repo's convention.

Usage:
  python3 scoutsync_uncategorized_round2_probe.py
"""
import json, os, urllib.request
from datetime import datetime, timedelta, timezone

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

DAYS = 180
TOP_N = 80


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
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    print(f"=== Round 2: Uncategorized services, trailing {DAYS} days (since {since}) ===\n")

    categories = supa_get("product_categories", "select=id,name&order=name.asc")
    print(f"-- {len(categories)} existing categories --")
    for c in categories:
        print(f"  {c['id']}: {c['name']}")

    rows = supa_get_all(
        "dispensed_items",
        f"select=product_name,subtotal_cents&product_category_id=is.null&dispensed_at=gte.{since}",
    )
    print(f"\n-- {len(rows)} uncategorized order-item rows in this window --")

    by_service = {}
    for r in rows:
        name = r.get("product_name") or "(blank product name)"
        s = by_service.setdefault(name, {"count": 0, "revenue": 0.0})
        s["count"] += 1
        s["revenue"] += (r.get("subtotal_cents") or 0) / 100.0

    ranked = sorted(by_service.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    total_uncategorized_revenue = sum(s["revenue"] for _, s in ranked)
    print(f"-- Total uncategorized revenue in window: ${total_uncategorized_revenue:,.2f} across {len(ranked)} distinct names --")
    print(f"-- Top {TOP_N} by revenue --")
    for name, s in ranked[:TOP_N]:
        print(f"  {s['count']:>5}x  ${s['revenue']:>10,.2f}   {name}")


if __name__ == "__main__":
    main()
