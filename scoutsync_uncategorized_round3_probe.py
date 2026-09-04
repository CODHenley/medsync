#!/usr/bin/env python3
"""
scoutsync_uncategorized_round3_probe.py
Round 3: after two batches (43 + 80 = 123 items) were applied and confirmed
live (Revenue by Source's Uncategorized total dropped $498,743 -> $236,278
-> $200,594 across both resyncs), what's left in the long tail?

Same shape as scoutsync_uncategorized_round2_probe.py, but:
  - no date window (all-time) to see the true remaining tail, not just a
    trailing slice
  - top 80 again

Read-only. Deleted once its purpose is served, per this repo's convention.

Usage:
  python3 scoutsync_uncategorized_round3_probe.py
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

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
    print("=== Round 3: Uncategorized services, all-time ===\n")

    categories = supa_get("product_categories", "select=id,name&order=name.asc")
    print(f"-- {len(categories)} existing categories --")
    for c in categories:
        print(f"  {c['id']}: {c['name']}")

    rows = supa_get_all(
        "dispensed_items",
        "select=product_name,subtotal_cents&product_category_id=is.null",
    )
    print(f"\n-- {len(rows)} uncategorized order-item rows (all-time) --")

    by_service = {}
    for r in rows:
        name = r.get("product_name") or "(blank product name)"
        s = by_service.setdefault(name, {"count": 0, "revenue": 0.0})
        s["count"] += 1
        s["revenue"] += (r.get("subtotal_cents") or 0) / 100.0

    ranked = sorted(by_service.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    total_uncategorized_revenue = sum(s["revenue"] for _, s in ranked)
    print(f"-- Total uncategorized revenue (all-time): ${total_uncategorized_revenue:,.2f} across {len(ranked)} distinct names --")
    print(f"-- Top {TOP_N} by revenue --")
    for name, s in ranked[:TOP_N]:
        print(f"  {s['count']:>5}x  ${s['revenue']:>10,.2f}   {name}")


if __name__ == "__main__":
    main()
