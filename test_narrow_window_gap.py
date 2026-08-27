#!/usr/bin/env python3
"""
test_narrow_window_gap.py
Read-only, one-off. Tests whether a specific known-missing Vetspire order
item appears in a NARROW usageReport query (the exact window shape
vetspire_intraday_sync.py actually sends: s=today-WIDE_LOOKBACK_DAYS,
e=today) versus a WIDE query (180-day lookback, the shape
reconcile_dispensed_items.py / diagnose_gap_wide_range.py use).

Old Orchard order_item_id 4181884522 (SKU GABAPESUS0066VC, qty 30,
updatedAt 2026-08-24) has been confirmed present in every wide-range
query this session, yet was never captured by intraday sync despite
being well inside its rolling 7-day window for 3+ days and hundreds of
sync runs. Every previously-diagnosed Vetspire windowing bug in this
repo assumed the flakiness was independent of query width. This checks
whether query width itself is a factor: if the item is reliably missing
from narrow queries specifically, that's a new, distinct failure mode
from the ones already fixed.
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

    print(f"=== Testing query-width sensitivity for order_item_id={args.order_item_id} at location={args.location} ===\n")

    # Run each width 3x back-to-back -- if it's plain non-determinism, presence should
    # flip between runs; if it's width-correlated, presence should be consistent per width.
    for run in range(1, 4):
        print(f"--- Run {run} ---")
        narrow_s = (today - timedelta(days=7)).isoformat()
        narrow_e = today.isoformat()
        check(token, args.location, narrow_s, narrow_e, "NARROW (7d, intraday-sync shape)", args.order_item_id)

        wide_s = (today - timedelta(days=180)).isoformat()
        wide_e = today.isoformat()
        check(token, args.location, wide_s, wide_e, "WIDE (180d, reconcile shape)", args.order_item_id)
        print()


if __name__ == "__main__":
    main()
