#!/usr/bin/env python3
"""
diagnose_dispensed_duplication.py
One-off: dump the raw Vetspire order items (id, updatedAt, quantity) for one
SKU/location/range side-by-side with the raw Supabase dispensed_items rows
(dispensed_at, quantity) for the same SKU/location/range, to see exactly how
backfill_date_range.py's day-by-day aggregation produced more rows/quantity
than real Vetspire order items — e.g. the same order item id appearing in
more than one single-day usageReport query (cross-day duplication from
loose date-range boundaries), since backfill_date_range.py ignores the
order item's own id and aggregates purely by which day-query returned it.

Read-only. No Supabase writes.

Usage:
  VETSPIRE_API_TOKEN="..." python3 diagnose_dispensed_duplication.py \
      --sku 98-11003-02 --location 28253 --start 2026-01-01 --end 2026-08-18
"""
import argparse, json, os, sys, urllib.request, urllib.error

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
            product { id name sku }
            quantity
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
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    token = load_token()

    print(f"\n=== Vetspire real order items: SKU={args.sku} location={args.location} {args.start}-{args.end} ===")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.start, "e": args.end})
    if "errors" in result:
        print(f"  ERROR: {result['errors']}"); sys.exit(1)
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    matched = [it for it in order_items if (it.get("product") or {}).get("sku") == args.sku]
    print(f"  {len(matched)} real order items (each should be one physical dispense event)")
    for it in sorted(matched, key=lambda x: x.get("updatedAt") or ""):
        print(f"    id={it.get('id')!s:>10}  updatedAt={it.get('updatedAt')}  qty={it.get('quantity')}  ret={it.get('returned')} ref={it.get('refunded')}")

    print(f"\n=== Supabase dispensed_items rows: same SKU/location/range ===")
    rows = supa_get(
        "dispensed_items",
        f"select=dispensed_at,quantity,returned,refunded,order_item_id,pulled_at&sku=eq.{args.sku}"
        f"&location_id=eq.{args.location}&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59&order=dispensed_at.asc",
    )
    print(f"  {len(rows)} rows")
    for r in rows:
        print(f"    dispensed_at={r.get('dispensed_at')}  qty={r.get('quantity')}  ret={r.get('returned')} ref={r.get('refunded')}  order_item_id={r.get('order_item_id')}  pulled_at={r.get('pulled_at')}")

    print(f"\n=== Totals ===")
    vet_total = sum(float(it.get("quantity") or 0) for it in matched if not it.get("returned") and not it.get("refunded"))
    supa_total = sum(float(r.get("quantity") or 0) for r in rows if not r.get("returned") and not r.get("refunded"))
    print(f"  Vetspire real total (excl ret/ref): {vet_total}")
    print(f"  Supabase stored total (excl ret/ref): {supa_total}")
    print(f"  {len(matched)} real events vs {len(rows)} stored rows")


if __name__ == "__main__":
    main()
