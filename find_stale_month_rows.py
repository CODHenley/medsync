#!/usr/bin/env python3
"""
find_stale_month_rows.py
Read-only (unless --delete is passed) scan of dispensed_items for stale
month-aggregated rows left over from an old dispensed_items_backfill.py run
(pre-dating this session) that are now duplicated by the day-level rows the
2026-08-18 backfill_date_range.py runs added for the same underlying events.

IMPORTANT: not every month-start row is a duplicate. Jan-Apr was only ever
backfilled at month granularity and never re-run at day level, so those
rows are the SOLE copy of that data. --delete only ever removes rows that
have a CONFIRMED same-month day-level replacement (i.e. genuinely
superseded duplicates) — a month row with no day-level counterpart is
always left untouched, no matter how "stale-pattern" it looks.

Usage:
  python3 find_stale_month_rows.py                # report only, no writes
  python3 find_stale_month_rows.py --delete        # delete CONFIRMED duplicates only
"""
import argparse, json, urllib.request, urllib.error
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

STALE_CUTOFF = "2026-08-06T00:00:00+00:00"  # anything pulled before the current live-pipeline era

LOCATIONS = {
    "11111111-0000-0000-0000-000000000001": "Lincoln Park",
    "11111111-0000-0000-0000-000000000002": "Old Orchard",
    "11111111-0000-0000-0000-000000000003": "West Loop",
    "11111111-0000-0000-0000-000000000004": "Wheaton",
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
    if not ids:
        return
    # PostgREST 'in' filter — chunk to keep URLs reasonable
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


def is_month_start(dispensed_at):
    # e.g. "2026-05-01T00:00:00+00:00"
    if not dispensed_at:
        return False
    return dispensed_at[8:10] == "01" and dispensed_at[11:19] == "00:00:00"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete", action="store_true", help="Actually delete the stale rows found")
    args = ap.parse_args()

    print("Fetching all dispensed_items rows in 2026-01-01..2026-08-18 (paginated)...")
    rows = supa_get_all(
        "dispensed_items",
        "select=id,location_id,vetspire_product_id,product_name,sku,dispensed_at,quantity,pulled_at"
        "&dispensed_at=gte.2026-01-01&dispensed_at=lte.2026-08-18T23:59:59&order=dispensed_at.asc",
    )
    print(f"  {len(rows)} total rows fetched")

    stale = [r for r in rows if is_month_start(r.get("dispensed_at")) and (r.get("pulled_at") or "") < STALE_CUTOFF]
    print(f"\n=== Stale-pattern rows (month-start + old pulled_at): {len(stale)} ===")
    print("(this includes legitimate Jan-Apr month rows with no day-level replacement — NOT safe to delete on its own)")

    # Only a row with a confirmed same-month day-level replacement (from today's
    # backfill_date_range.py runs) is an actual duplicate. A month row with no
    # day-level counterpart (e.g. Jan-Apr, never re-backfilled at day level) is
    # the ONLY copy of that data and must never be touched.
    fresh_keys = set()
    for r in rows:
        if (r.get("pulled_at") or "") >= STALE_CUTOFF and not is_month_start(r.get("dispensed_at")):
            fresh_keys.add((r.get("location_id"), r.get("vetspire_product_id"), (r.get("dispensed_at") or "")[:7]))
    confirmed = [
        r for r in stale
        if (r.get("location_id"), r.get("vetspire_product_id"), (r.get("dispensed_at") or "")[:7]) in fresh_keys
    ]
    print(f"Confirmed duplicates (safe to delete — have a same-month day-level replacement): {len(confirmed)} / {len(stale)}")

    def summarize(label, records):
        by_loc = defaultdict(lambda: {"count": 0, "qty": 0.0})
        by_month = defaultdict(lambda: {"count": 0, "qty": 0.0})
        for r in records:
            loc = LOCATIONS.get(r.get("location_id"), r.get("location_id"))
            by_loc[loc]["count"] += 1
            by_loc[loc]["qty"] += float(r.get("quantity") or 0)
            month = (r.get("dispensed_at") or "")[:7]
            by_month[month]["count"] += 1
            by_month[month]["qty"] += float(r.get("quantity") or 0)
        print(f"\n--- {label}: {len(records)} rows ---")
        print("By location:")
        for loc, d in sorted(by_loc.items()):
            print(f"  {loc:15s}  {d['count']:4d} rows   {d['qty']:10.1f} total qty")
        print("By month:")
        for month, d in sorted(by_month.items()):
            print(f"  {month}  {d['count']:4d} rows   {d['qty']:10.1f} total qty")
        total = sum(float(r.get("quantity") or 0) for r in records)
        print(f"Total quantity: {total}")
        return total

    summarize("ALL stale-pattern rows (for context only)", stale)
    confirmed_total = summarize("CONFIRMED duplicates (the only ones --delete removes)", confirmed)

    not_confirmed = len(stale) - len(confirmed)
    if not_confirmed:
        print(f"\n{not_confirmed} stale-pattern rows have NO day-level replacement — left untouched (likely Jan-Apr, sole copy of that data).")

    if args.delete:
        print(f"\n=== DELETING {len(confirmed)} confirmed-duplicate rows (qty {confirmed_total}) ===")
        supa_delete_by_ids([r["id"] for r in confirmed])
        print("Done.")
    else:
        print("\n(dry run — pass --delete to actually remove the CONFIRMED duplicate rows only)")


if __name__ == "__main__":
    main()
