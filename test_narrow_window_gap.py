#!/usr/bin/env python3
"""
test_narrow_window_gap.py
Read-only, one-off. Confirmed (first pass, 7d vs 180d, 3 repeats each):
order_item_id 4181884522 (Old Orchard, SKU GABAPESUS0066VC, qty 30,
updatedAt 2026-08-24) is DETERMINISTICALLY absent from every narrow
(7-day) usageReport query and DETERMINISTICALLY present in every wide
(180-day) query -- not random flakiness, a real query-width threshold
effect. This is a new failure mode: every previously-diagnosed Vetspire
windowing bug in this repo assumed flakiness was independent of query
width (same window, different call, different result).

This sweeps intermediate widths (7/14/21/30/45/60/90/120/150/180 days,
all ending "today") to find roughly where the item starts reliably
appearing, so vetspire_intraday_sync.py's WIDE_LOOKBACK_DAYS can be set
to a value proven sufficient instead of guessed -- going straight to
180 would mean re-upserting ~17k rows every 5 minutes, so the goal is
the smallest width that reliably works, not the largest that's safe.
"""
import argparse, json, os, sys, urllib.request
from datetime import date, timedelta

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id updatedAt }
    }
}
"""


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if token:
        return token.removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set.")


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
        "Origin":        VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def check(token, loc_id, s, e, label, target_id):
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": s, "e": e})
    if "errors" in result:
        print(f"  [{label}] ERROR: {result['errors'][0]['message'][:200]}")
        return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    ids = {str(it.get("id")) for it in items}
    present = target_id in ids
    print(f"  [{label}] window {s}..{e}: {len(ids)} distinct items, target present={present}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--order-item-id", required=True)
    args = ap.parse_args()

    token = load_token()
    today = date.today()

    print(f"=== Sweeping query width for order_item_id={args.order_item_id} at location={args.location} ===\n")

    for days in (7, 14, 21, 30, 45, 60, 90, 120, 150, 180):
        s = (today - timedelta(days=days)).isoformat()
        e = today.isoformat()
        check(token, args.location, s, e, f"{days:>3d}d", args.order_item_id)


if __name__ == "__main__":
    main()
