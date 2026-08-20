#!/usr/bin/env python3
"""
diagnose_reconciliation_gap.py
Read-only. For one location over a date range, break down Vetspire's real
usageReport order items vs Supabase's stored dispensed_items rows PER SKU,
so a location-wide reconciliation mismatch (found by
reconcile_dispensed_items.py) can be traced to the specific product(s) and
rows responsible, instead of guessing.

Also reports how many Supabase rows in range have order_item_id IS NULL
(legacy aggregated rows, pre-dating the order_item_id-as-sole-key fix) vs
populated, since coexistence of both for the same window is the known
duplication pattern.

Usage:
  VETSPIRE_API_TOKEN="..." python3 diagnose_reconciliation_gap.py \
      --location 23083 --start 2026-08-04 --end 2026-08-17
"""
import argparse, json, os, sys, urllib.request
from collections import defaultdict

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            product { sku name }
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
    args = ap.parse_args()

    token = load_token()

    print(f"=== Vetspire real order items: location={args.location} {args.start}..{args.end} ===")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.start, "e": args.end})
    if "errors" in result:
        print(f"  ERROR: {result['errors']}"); sys.exit(1)
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    print(f"  {len(order_items)} total order items returned")

    vet_by_sku = defaultdict(lambda: {"qty": 0.0, "ids": set()})
    for it in order_items:
        if it.get("returned") or it.get("refunded"):
            continue
        sku = (it.get("product") or {}).get("sku") or "UNKNOWN"
        vet_by_sku[sku]["qty"] += float(it.get("quantity") or 0)
        vet_by_sku[sku]["ids"].add(str(it.get("id")))

    print(f"\n=== Supabase dispensed_items rows: location_id={args.location} {args.start}..{args.end} ===")
    rows = supa_get_all(
        "dispensed_items",
        f"select=sku,quantity,returned,refunded,order_item_id,dispensed_at,pulled_at"
        f"&location_id=eq.{args.location}&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    print(f"  {len(rows)} total rows")
    null_oid = [r for r in rows if not r.get("order_item_id")]
    pop_oid  = [r for r in rows if r.get("order_item_id")]
    print(f"  order_item_id IS NULL:  {len(null_oid)} rows (legacy/aggregated-style)")
    print(f"  order_item_id populated: {len(pop_oid)} rows")
    if null_oid:
        pulled_ats = sorted(set(r.get("pulled_at") for r in null_oid))
        print(f"  NULL-oid rows pulled_at range: {pulled_ats[0]} .. {pulled_ats[-1]}")
        dispensed_ats = sorted(set(r.get("dispensed_at") for r in null_oid))
        print(f"  NULL-oid rows span {len(dispensed_ats)} distinct dispensed_at values, e.g. {dispensed_ats[:5]}")

    supa_by_sku = defaultdict(lambda: {"qty": 0.0, "oids": set(), "n": 0})
    for r in rows:
        if r.get("returned") or r.get("refunded"):
            continue
        sku = r.get("sku") or "UNKNOWN"
        supa_by_sku[sku]["qty"] += float(r.get("quantity") or 0)
        supa_by_sku[sku]["n"] += 1
        if r.get("order_item_id"):
            supa_by_sku[sku]["oids"].add(r.get("order_item_id"))

    print(f"\n=== Per-SKU comparison (excl returned/refunded) ===")
    all_skus = sorted(set(vet_by_sku) | set(supa_by_sku))
    for sku in all_skus:
        v = vet_by_sku.get(sku, {"qty": 0.0, "ids": set()})
        s = supa_by_sku.get(sku, {"qty": 0.0, "n": 0, "oids": set()})
        diff = v["qty"] - s["qty"]
        if abs(diff) < 0.01:
            continue
        print(f"  {sku:16s}  vetspire_qty={v['qty']:8.2f} ({len(v['ids'])} items)   "
              f"supabase_qty={s['qty']:8.2f} ({s['n']} rows, {len(s['oids'])} distinct order_item_id)   diff={diff:+8.2f}")

    vet_total = sum(v["qty"] for v in vet_by_sku.values())
    supa_total = sum(s["qty"] for s in supa_by_sku.values())
    print(f"\n  TOTAL: vetspire={vet_total:.2f}  supabase={supa_total:.2f}  diff={vet_total - supa_total:+.2f}")


if __name__ == "__main__":
    main()
