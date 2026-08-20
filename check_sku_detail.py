#!/usr/bin/env python3
"""
check_sku_detail.py
Read-only. For one location/date-range/SKU, lists every Supabase
dispensed_items row for that SKU alongside Vetspire's CURRENT record for
that exact order_item_id (re-queried individually over a wide range), so a
per-SKU quantity mismatch found by diagnose_reconciliation_gap.py can be
traced to the one specific row responsible instead of guessing.
"""
import argparse, json, os, urllib.request
from datetime import date

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
    ap.add_argument("--wide-start", default="2026-01-01")
    args = ap.parse_args()

    token = load_token()

    print(f"Fetching Supabase rows for location={args.location} sku={args.sku} {args.start}..{args.end}...")
    rows = supa_get_all(
        "dispensed_items",
        f"select=id,order_item_id,quantity,returned,refunded,dispensed_at,pulled_at,vetspire_product_id"
        f"&location_id=eq.{args.location}&sku=eq.{args.sku}"
        f"&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    print(f"  {len(rows)} rows stored\n")

    wide_end = date.today().isoformat()
    print(f"Fetching Vetspire's CURRENT view over a wide range {args.wide_start}..{wide_end}...")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.wide_start, "e": wide_end})
    if "errors" in result:
        print(f"ERROR: {result['errors']}"); return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    vet_by_id = {str(it.get("id")): it for it in order_items}
    print(f"  {len(vet_by_id)} distinct order items found in wide range\n")

    print("=== Row-by-row comparison ===")
    for row in rows:
        oid = row.get("order_item_id")
        vit = vet_by_id.get(oid)
        if not vit:
            print(f"  order_item_id={oid}  supabase_qty={row.get('quantity')}  "
                  f"dispensed_at={row.get('dispensed_at')}  pulled_at={row.get('pulled_at')}  "
                  f"vetspire_product_id={row.get('vetspire_product_id')}  =>  NOT FOUND anywhere in Vetspire (voided)")
            continue
        vit_sku = (vit.get("product") or {}).get("sku")
        vit_pid = vit.get("productId") or (vit.get("product") or {}).get("id")
        same_product = str(vit_pid) == str(row.get("vetspire_product_id"))
        print(f"  order_item_id={oid}  supabase_qty={row.get('quantity')}  "
              f"stored_dispensed_at={row.get('dispensed_at')}  vetspire_product_id_stored={row.get('vetspire_product_id')}  "
              f"=>  vetspire_qty={vit.get('quantity')}  vetspire_productId={vit_pid}  vetspire_sku={vit_sku}  "
              f"vetspire_updatedAt={vit.get('updatedAt')}  returned={vit.get('returned')}  refunded={vit.get('refunded')}  "
              f"product_changed={not same_product}")


if __name__ == "__main__":
    main()
