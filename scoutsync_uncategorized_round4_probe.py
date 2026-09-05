#!/usr/bin/env python3
"""
scoutsync_uncategorized_round4_probe.py
Round 4: the "Uncategorized -- services" drill-down still shows real, nameable
products/services the same way rounds 1-3 did (Ketamine HCl Inj, Fenbendazole
Susp, Zymox Otic, etc.) -- user confirmed these are all things that CAN be
categorized in Vetspire, same as before. This lists every currently
distinct uncategorized product_name (all-time, no date limit) with revenue,
plus the full 18-category reference list with real ids, so the actual
scoutsync_bulk_category_apply_round4.py mapping can be written against real
ids instead of guessing.

Report-only. No Vetspire writes. Delete once its purpose is served, per
this repo's convention for one-off diagnostics.

Usage:
  python3 scoutsync_uncategorized_round4_probe.py
"""
import json, urllib.request

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        page = get(path, f"{params}&limit={page_size}&offset={offset}")
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def main():
    print("=== Full product_categories reference (real ids + names) ===")
    cats = get("product_categories", "select=id,name&order=name.asc")
    for c in cats:
        print(f"  {c['id']}: {c['name']}")
    print(f"  ({len(cats)} categories)\n")

    print("=== All currently-uncategorized dispensed_items, grouped by product_name ===")
    rows = get_all(
        "dispensed_items",
        "select=vetspire_product_id,product_name,subtotal_cents&product_category_id=is.null",
    )
    by_name = {}
    for r in rows:
        name = (r.get("product_name") or "").strip()
        entry = by_name.setdefault(name, {"count": 0, "revenue": 0.0, "product_id": r.get("vetspire_product_id")})
        entry["count"] += 1
        entry["revenue"] += float(r.get("subtotal_cents") or 0) / 100.0

    total_count = sum(v["count"] for v in by_name.values())
    total_revenue = sum(v["revenue"] for v in by_name.values())
    print(f"  {len(by_name)} distinct names, {total_count} instances, ${total_revenue:,.2f} total\n")

    for name, v in sorted(by_name.items(), key=lambda kv: kv[1]["revenue"], reverse=True):
        print(f"  {name!r}: product_id={v['product_id']}, count={v['count']}, revenue=${v['revenue']:,.2f}")


if __name__ == "__main__":
    main()
