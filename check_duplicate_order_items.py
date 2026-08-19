#!/usr/bin/env python3
"""
check_duplicate_order_items.py
Read-only. Checks whether any (order_item_id, location_id) pair appears
more than once in dispensed_items — this should be structurally impossible
given the unique index added in dispensed_items_order_item_id_sole_key.sql,
so any duplicate found here means that index isn't actually enforcing
uniqueness (or was dropped), which would explain a location's Supabase
total running ~2x Vetspire's.
"""
import argparse, json, urllib.request
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}",
            headers={
                "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                "Range": f"{offset}-{offset + page_size - 1}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            chunk = json.loads(r.read())
        out.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    rows = supa_get_all(
        "dispensed_items",
        f"select=id,order_item_id,quantity,pulled_at,dispensed_at,returned,refunded"
        f"&location_id=eq.{args.location}&order_item_id=not.is.null"
        f"&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    print(f"Total order_item_id-populated rows in range: {len(rows)}")

    by_oid = defaultdict(list)
    for r in rows:
        by_oid[r["order_item_id"]].append(r)

    dupes = {oid: rs for oid, rs in by_oid.items() if len(rs) > 1}
    print(f"Distinct order_item_id values: {len(by_oid)}")
    print(f"order_item_id values appearing MORE THAN ONCE: {len(dupes)}")

    total_extra_rows = sum(len(rs) - 1 for rs in dupes.values())
    print(f"Extra (duplicate) rows beyond the first occurrence: {total_extra_rows}")

    for oid, rs in list(dupes.items())[:10]:
        print(f"\n  order_item_id={oid}  ({len(rs)} rows)")
        for r in rs:
            print(f"    id={r['id']} qty={r['quantity']} dispensed_at={r['dispensed_at']} "
                  f"pulled_at={r['pulled_at']} returned={r['returned']} refunded={r['refunded']}")


if __name__ == "__main__":
    main()
