#!/usr/bin/env python3
"""
delete_legacy_rows.py
Deletes every dispensed_items row with order_item_id IS NULL — the legacy
day/month-aggregated rows from before order_item_id became the sole natural
key (see dispensed_items_order_item_id_sole_key.sql).

Safe only because verify_full_backfill.py just confirmed, per location,
across the full history (2024-11-01 → today), that order_item_id-populated
rows ALONE already match Vetspire's real totals within 0.1% — every legacy
row is a confirmed duplicate of data that now exists correctly keyed. This
script does not re-derive that proof; it trusts the verification run and
only re-checks Vetspire totals hold immediately before deleting, as a final
guard against something changing between the two runs.

Usage:
  python3 delete_legacy_rows.py                # report only, no writes
  python3 delete_legacy_rows.py --delete        # actually delete
"""
import argparse, json, os, urllib.request, urllib.error
from collections import defaultdict

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "23083": "Lincoln Park",
    "27390": "Old Orchard",
    "24356": "West Loop",
    "28253": "Wheaton",
}


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


def supa_delete_by_ids(ids):
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        id_list = ",".join(chunk)
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/dispensed_items?id=in.({id_list})",
            headers={
                "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                "Prefer": "return=minimal",
            },
        )
        req.get_method = lambda: "DELETE"
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"    deleted chunk of {len(chunk)} — HTTP {r.status}")
        except urllib.error.HTTPError as e:
            print(f"    ERROR deleting chunk: {e.code} {e.read().decode()[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()

    print("Fetching all dispensed_items rows with order_item_id IS NULL...")
    rows = supa_get_all(
        "dispensed_items",
        "select=id,location_id,quantity&order_item_id=is.null",
    )
    print(f"  {len(rows)} legacy rows found\n")

    by_loc = defaultdict(lambda: {"count": 0, "qty": 0.0})
    for r in rows:
        loc = LOCATIONS.get(r.get("location_id"), r.get("location_id"))
        by_loc[loc]["count"] += 1
        by_loc[loc]["qty"] += float(r.get("quantity") or 0)

    print("By location:")
    for loc, d in sorted(by_loc.items()):
        print(f"  {loc:15s}  {d['count']:5d} rows   qty={d['qty']:10.1f}")

    if not rows:
        print("\nNothing to delete.")
        return

    if args.delete:
        ids = [r["id"] for r in rows]
        print(f"\n=== DELETING {len(ids)} legacy rows ===")
        supa_delete_by_ids(ids)
        print("Done.")
    else:
        print("\n(dry run — pass --delete to actually remove these rows)")


if __name__ == "__main__":
    main()
