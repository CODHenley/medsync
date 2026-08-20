#!/usr/bin/env python3
"""
diagnose_gap_wide_range.py
Read-only. Same per-SKU breakdown as diagnose_reconciliation_gap.py, but
using the wide-range + client-side date filter method now used by
reconcile_dispensed_items.py, instead of trusting Vetspire's own
startDate/endDate windowing (confirmed unreliable — see
reconcile_dispensed_items.py's module docstring). Use this whenever a
wide-range-confirmed reconcile mismatch needs to be traced to a specific
SKU; diagnose_reconciliation_gap.py's own windowed total cannot be trusted
for this anymore.
"""
import argparse, json, os, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

WIDE_LOOKBACK_DAYS = 180

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id productId product { id sku name } quantity returned refunded updatedAt }
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
    args = ap.parse_args()

    token = load_token()
    wide_start = (datetime.strptime(args.start, "%Y-%m-%d").date() - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()

    print(f"=== Vetspire wide-range query: location={args.location} {wide_start}..{args.end}, "
          f"filtered client-side to {args.start}..{args.end} ===")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": wide_start, "e": args.end})
    if "errors" in result:
        print(f"  ERROR: {result['errors']}"); sys.exit(1)
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    by_id = {str(it.get("id")): it for it in order_items}
    print(f"  {len(by_id)} distinct order items in wide range")

    vet_by_sku = defaultdict(lambda: {"qty": 0.0, "ids": set()})
    for it in by_id.values():
        if it.get("returned") or it.get("refunded"):
            continue
        if not (it.get("productId") or (it.get("product") or {}).get("id")):
            continue
        updated = (it.get("updatedAt") or "")[:10]
        if not (args.start <= updated <= args.end):
            continue
        sku = (it.get("product") or {}).get("sku") or "UNKNOWN"
        vet_by_sku[sku]["qty"] += float(it.get("quantity") or 0)
        vet_by_sku[sku]["ids"].add(str(it.get("id")))

    print(f"\n=== Supabase dispensed_items rows: location_id={args.location} {args.start}..{args.end} ===")
    rows = supa_get_all(
        "dispensed_items",
        f"select=sku,quantity,returned,refunded,order_item_id,dispensed_at"
        f"&location_id=eq.{args.location}&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    print(f"  {len(rows)} total rows")

    supa_by_sku = defaultdict(lambda: {"qty": 0.0, "oids": set(), "n": 0})
    for r in rows:
        if r.get("returned") or r.get("refunded"):
            continue
        sku = r.get("sku") or "UNKNOWN"
        supa_by_sku[sku]["qty"] += float(r.get("quantity") or 0)
        supa_by_sku[sku]["n"] += 1
        if r.get("order_item_id"):
            supa_by_sku[sku]["oids"].add(r.get("order_item_id"))

    print(f"\n=== Per-SKU comparison (excl returned/refunded, productId-filtered, wide-range method) ===")
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
