#!/usr/bin/env python3
"""
diagnose_dispensed_gap.py
One-off diagnostic for the recurring "dispensed qty doesn't match Vetspire's
own Usage Report" gap (e.g. Catalyst Chem 17 @ Wheaton: 71 in MedSync vs 78
in Vetspire for the same YTD range).

Compares three things for one product/location/date range:
  1. Vetspire's usageReport total, queried in ONE request spanning the whole
     range (matches how Vetspire's own Usage Report page computes its total —
     no day-by-day chunking to introduce boundary ambiguity).
  2. What's actually stored in Supabase's dispensed_items for the same
     product/location/range.
  3. A breakdown of the Vetspire-side records by hour-of-day (from
     updatedAt), to check whether missing quantity concentrates in the
     evening hours — which would point at a UTC-vs-Central-time day-boundary
     bug in vetspire_intraday_sync.py's `date.today()` (computed on the UTC
     GitHub Actions runner clock, not Wheaton's Central practice time).

Usage:
  VETSPIRE_API_TOKEN="..." python3 diagnose_dispensed_gap.py \
      --sku 98-11003-02 --location 28253 --start 2026-01-01 --end 2026-08-18
"""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            productId
            product { id name sku unitCost }
            quantity
            quantityRemaining
            unitPrice
            returned
            refunded
            updatedAt
        }
    }
}
"""


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if token:
        return token.removeprefix("Bearer ").strip()
    for path in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetspire_token.txt"),
        os.path.expanduser("~/.vetspire_token"),
    ):
        if os.path.exists(path):
            return open(path).read().strip().removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set and no token file found.")


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
        "Origin":        VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sku", required=True)
    ap.add_argument("--location", required=True, help="Vetspire numeric location id, e.g. 28253")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    token = load_token()

    print(f"\n=== Vetspire usageReport: SKU={args.sku} location={args.location} {args.start}→{args.end} ===")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.start, "e": args.end})
    if "errors" in result:
        print(f"  ERROR: {result['errors']}")
        sys.exit(1)

    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = (usage_raw.get("orderItems", []) if isinstance(usage_raw, dict)
                   else usage_raw if isinstance(usage_raw, list) else [])
    print(f"  {len(order_items)} total order items returned for this location/range (all products)")

    matched = [it for it in order_items if (it.get("product") or {}).get("sku") == args.sku]
    print(f"  {len(matched)} order items match SKU {args.sku}")

    vet_total = 0.0
    vet_total_excl_ret = 0.0
    by_hour = {}
    vetspire_product_id = None
    for it in matched:
        prod = it.get("product") or {}
        vetspire_product_id = it.get("productId") or prod.get("id")
        qty = float(it.get("quantity") or 0)
        vet_total += qty
        excluded = bool(it.get("returned")) or bool(it.get("refunded"))
        if not excluded:
            vet_total_excl_ret += qty
        updated = it.get("updatedAt") or ""
        hour = updated[11:13] if len(updated) >= 13 else "??"
        by_hour[hour] = by_hour.get(hour, 0) + (0 if excluded else qty)

    print(f"\n  Vetspire product id: {vetspire_product_id}")
    print(f"  Vetspire TOTAL quantity (incl. returned/refunded): {vet_total}")
    print(f"  Vetspire TOTAL quantity (excl. returned/refunded): {vet_total_excl_ret}")
    print(f"\n  Breakdown by hour-of-day (updatedAt, excl. returned/refunded):")
    for hour in sorted(by_hour):
        print(f"    {hour}:00  {by_hour[hour]}")

    print(f"\n=== Supabase dispensed_items: same SKU/location/range ===")
    rows = supa_get(
        "dispensed_items",
        f"select=quantity,returned,refunded,dispensed_at&sku=eq.{args.sku}"
        f"&location_id=eq.{args.location}&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    print(f"  {len(rows)} rows in dispensed_items")
    supa_total = sum(float(r.get("quantity") or 0) for r in rows)
    supa_total_excl_ret = sum(
        float(r.get("quantity") or 0) for r in rows
        if not r.get("returned") and not r.get("refunded")
    )
    print(f"  Supabase TOTAL quantity (incl. returned/refunded): {supa_total}")
    print(f"  Supabase TOTAL quantity (excl. returned/refunded): {supa_total_excl_ret}")

    print(f"\n=== Diff ===")
    diff = vet_total_excl_ret - supa_total_excl_ret
    print(f"  Vetspire (excl. ret/ref) - Supabase (excl. ret/ref) = {diff}")
    if abs(diff) < 0.001:
        print("  MATCH — no gap.")
    else:
        print(f"  GAP of {diff} units. Check the hour-of-day breakdown above for a concentration")
        print(f"  in the evening hours (roughly hour 00-05 UTC = 6pm-11pm CST) — that pattern points")
        print(f"  at vetspire_intraday_sync.py computing 'today' from the UTC runner clock instead")
        print(f"  of Wheaton's Central practice time, mis-bucketing evening dispensing.")


if __name__ == "__main__":
    main()
