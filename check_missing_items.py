#!/usr/bin/env python3
"""
check_missing_items.py
Read-only. For one location/date-range/SKU, finds Vetspire order items
(via the wide-range + client-side date filter method) that have NO
matching row in Supabase's dispensed_items at all — the reverse direction
of check_sku_detail.py, which starts from Supabase rows. Used to
characterize a per-SKU diff found by diagnose_gap_wide_range.py: is the
missing item recent (a backfill-lag artifact that self-heals) or old (a
genuine capture gap)?
"""
import argparse, json, os, urllib.request
from datetime import datetime, timedelta

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

WIDE_LOOKBACK_DAYS = 180

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id productId product { id sku } quantity returned refunded updatedAt }
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


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&order=id",
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
    ap.add_argument("--sku", required=True)
    args = ap.parse_args()

    token = load_token()
    wide_start = (datetime.strptime(args.start, "%Y-%m-%d").date() - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()

    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": wide_start, "e": args.end})
    if "errors" in result:
        print(f"ERROR: {result['errors']}"); return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    by_id = {str(it.get("id")): it for it in order_items}

    matching = []
    for it in by_id.values():
        if it.get("returned") or it.get("refunded"):
            continue
        sku = (it.get("product") or {}).get("sku")
        if sku != args.sku:
            continue
        updated = (it.get("updatedAt") or "")[:10]
        if not (args.start <= updated <= args.end):
            continue
        matching.append(it)
    print(f"Vetspire order items for sku={args.sku} in {args.start}..{args.end}: {len(matching)}")

    print(f"\nFetching Supabase order_item_ids for location={args.location} sku={args.sku} (no date filter, all-time)...")
    rows = supa_get_all(
        "dispensed_items",
        f"select=order_item_id&location_id=eq.{args.location}&sku=eq.{args.sku}",
    )
    supa_ids = {r.get("order_item_id") for r in rows if r.get("order_item_id")}
    print(f"  {len(supa_ids)} order_item_ids stored for this SKU (all-time, this location)\n")

    missing = [it for it in matching if str(it.get("id")) not in supa_ids]
    print(f"=== {len(missing)} Vetspire item(s) with NO matching Supabase row at all ===")
    for it in missing:
        print(f"  order_item_id={it.get('id')}  quantity={it.get('quantity')}  "
              f"updatedAt={it.get('updatedAt')}  productId={it.get('productId')}")


if __name__ == "__main__":
    main()
