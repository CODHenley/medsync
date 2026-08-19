#!/usr/bin/env python3
"""
check_pagination_limit.py
Read-only. Tests whether Vetspire's usageReport silently truncates results
for a high-volume date range instead of genuinely returning fewer items.
Queries the same location+range as ONE call, then again split into two
halves, and compares total item counts. If the halves sum to more than the
single call, usageReport is truncating rather than returning complete data.
"""
import argparse, json, os, urllib.request
from datetime import date, timedelta

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id quantity returned refunded }
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


def fetch_items(token, loc_id, start, end):
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": start, "e": end})
    if "errors" in result:
        raise RuntimeError(result["errors"][0]["message"][:200])
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    return usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    token = load_token()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    mid = start + (end - start) // 2

    print(f"=== Full range: {start} .. {end} ===")
    full_items = fetch_items(token, args.location, start.isoformat(), end.isoformat())
    full_ids = {it.get("id") for it in full_items}
    print(f"  {len(full_items)} items returned, {len(full_ids)} distinct ids")

    print(f"\n=== Half A: {start} .. {mid} ===")
    half_a = fetch_items(token, args.location, start.isoformat(), mid.isoformat())
    ids_a = {it.get("id") for it in half_a}
    print(f"  {len(half_a)} items returned, {len(ids_a)} distinct ids")

    mid_next = mid + timedelta(days=1)
    print(f"\n=== Half B: {mid_next} .. {end} ===")
    half_b = fetch_items(token, args.location, mid_next.isoformat(), end.isoformat())
    ids_b = {it.get("id") for it in half_b}
    print(f"  {len(half_b)} items returned, {len(ids_b)} distinct ids")

    combined_ids = ids_a | ids_b
    print(f"\n=== Comparison ===")
    print(f"  Full-range call:      {len(full_ids)} distinct ids")
    print(f"  Half A + Half B:      {len(combined_ids)} distinct ids ({len(ids_a)} + {len(ids_b)}, overlap {len(ids_a & ids_b)})")
    missing_from_full = combined_ids - full_ids
    print(f"  Ids in halves but NOT in full-range call: {len(missing_from_full)}")
    if missing_from_full:
        print("  ⚠ TRUNCATION SUSPECTED — the full-range call is missing items the halves found.")
        sample = list(missing_from_full)[:10]
        for it in full_items + half_a + half_b:
            if it.get("id") in sample:
                print(f"    id={it.get('id')} qty={it.get('quantity')} returned={it.get('returned')} refunded={it.get('refunded')}")
    else:
        print("  No truncation detected — full-range call has all ids the halves found.")


if __name__ == "__main__":
    main()
