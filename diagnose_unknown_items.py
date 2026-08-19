#!/usr/bin/env python3
"""
diagnose_unknown_items.py
Read-only. Samples Vetspire order items that backfill_date_range.py would
skip (no resolvable productId/product.id) or that have no product.sku, to
determine whether they are legitimately non-inventory line items (service
fees, exam charges) or real dispensed-product events being silently
dropped by the "skip if no product id" logic.
"""
import argparse, json, os, urllib.request

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

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
            subtotalCents
            totalBeforeTaxCents
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    token = load_token()
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.start, "e": args.end})
    if "errors" in result:
        print(f"ERROR: {result['errors']}")
        return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    print(f"Total order items in range: {len(order_items)}")

    no_pid = []
    no_sku_but_has_pid = []
    for it in order_items:
        prod = it.get("product") or {}
        pid = it.get("productId") or prod.get("id")
        if not pid:
            no_pid.append(it)
        elif not prod.get("sku"):
            no_sku_but_has_pid.append(it)

    total_qty_all = sum(float(it.get("quantity") or 0) for it in order_items
                         if not it.get("returned") and not it.get("refunded"))
    total_qty_no_pid = sum(float(it.get("quantity") or 0) for it in no_pid
                            if not it.get("returned") and not it.get("refunded"))

    print(f"\n=== Items with NO productId/product.id (would be SKIPPED by backfill): {len(no_pid)} ===")
    print(f"    quantity sum (excl ret/ref): {total_qty_no_pid:.2f}  (out of total {total_qty_all:.2f})")
    for it in no_pid[:15]:
        print(f"  id={it.get('id')} qty={it.get('quantity')} unitPrice={it.get('unitPrice')} "
              f"subtotalCents={it.get('subtotalCents')} returned={it.get('returned')} refunded={it.get('refunded')} "
              f"updatedAt={it.get('updatedAt')} product={it.get('product')} productId={it.get('productId')}")

    print(f"\n=== Items WITH productId but no product.sku: {len(no_sku_but_has_pid)} ===")
    for it in no_sku_but_has_pid[:10]:
        print(f"  id={it.get('id')} productId={it.get('productId')} product={it.get('product')} "
              f"qty={it.get('quantity')} updatedAt={it.get('updatedAt')}")


if __name__ == "__main__":
    main()
