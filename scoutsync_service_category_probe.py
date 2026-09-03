#!/usr/bin/env python3
"""
scoutsync_service_category_probe.py
One-off probe: can a "services within a category, with instance counts"
drill-down be built on top of the existing dispensed_items pipeline
(usageReport.orderItems)?

Two open questions this answers, live against production:
  1. Product.productCategories is a confirmed-real field in the schema
     (see introspect_output.txt) but was never actually queried or tested.
     Does it return a list or a single object? Does it come back populated
     at all for real products?
  2. Do the category ids it returns land in the SAME id space as
     product_categories (synced separately via `productCategories { id name }`
     in vetspire_financial_sync.py, which backs Revenue by Source today)?
     If not, a drill-down keyed on product_category_id would silently show
     the wrong category names.

As a secondary sanity check (does dispensed_items really cover "all billed
items" the way dispensed_items_backfill.py's docstring claims, or mostly
just pharmacy/inventory-tracked products?): compares total orderItems
subtotalCents for one location/week against that same location/week's
already-synced invoice_line_items revenue. A huge gap would mean
dispensed_items isn't a reliable stand-in for "everything billed" and a
category drill-down built on it would under-represent true revenue.

Read-only. Deleted once its purpose is served, per this repo's convention.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_service_category_probe.py
"""
import json, os, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATION_ID = "23083"  # Lincoln Park -- highest volume, best chance of hitting edge cases
DAYS = 14

USAGE_QUERY_WITH_CATEGORY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            productId
            product { id name productCategories { id name } }
            subtotalCents
        }
    }
}
"""

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                breakdowns:[PROVIDER_ID, PRODUCT_CATEGORY_ID], segment:DAY)
}
"""


def gql(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": token,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:500]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip().removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)
    s_str, e_str = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    print(f"=== Window: {s_str}..{e_str}, location {LOCATION_ID} ===\n")

    # ── Part 1: what does Product.productCategories actually look like? ──
    result = gql(token, USAGE_QUERY_WITH_CATEGORY, {"lids": [LOCATION_ID], "s": s_str, "e": e_str})
    if "errors" in result:
        print("USAGE QUERY ERRORS (productCategories subselection may be invalid):")
        print(json.dumps(result["errors"], indent=2)[:2000])
        return
    items = ((result.get("data") or {}).get("usageReport") or {}).get("orderItems") or []
    print(f"Fetched {len(items)} order items.\n")

    shape_examples = []
    products_with_categories = 0
    products_without_categories = 0
    distinct_product_ids_seen = set()
    category_id_counts = {}
    total_subtotal_cents = 0

    for it in items:
        total_subtotal_cents += it.get("subtotalCents") or 0
        prod = it.get("product") or {}
        pid = prod.get("id")
        if pid and pid not in distinct_product_ids_seen:
            distinct_product_ids_seen.add(pid)
            if len(shape_examples) < 5:
                shape_examples.append({"product_id": pid, "name": prod.get("name"), "productCategories_raw": prod.get("productCategories")})
        cats = prod.get("productCategories")
        if not cats:
            products_without_categories += 1
            continue
        products_with_categories += 1
        # Handle both possible shapes defensively -- this is exactly the
        # ambiguity being probed (list vs single object).
        cat_list = cats if isinstance(cats, list) else [cats]
        for c in cat_list:
            if isinstance(c, dict) and c.get("id") is not None:
                category_id_counts[c["id"]] = category_id_counts.get(c["id"], 0) + 1

    print("--- Raw shape, first 5 distinct products seen ---")
    print(json.dumps(shape_examples, indent=2))
    print(f"\nDistinct products seen: {len(distinct_product_ids_seen)}")
    print(f"Order-item rows whose product HAD a productCategories value: {products_with_categories}")
    print(f"Order-item rows whose product had NO productCategories value: {products_without_categories}")

    # ── Part 2: does that id space match the already-synced product_categories table? ──
    known_categories = supa_get("product_categories", "select=id,name")
    known_ids = {str(c["id"]) for c in known_categories}
    print(f"\n--- Cross-check against product_categories table ({len(known_categories)} known categories) ---")
    matched, unmatched = 0, 0
    for cid, n in category_id_counts.items():
        hit = str(cid) in known_ids
        matched += n if hit else 0
        unmatched += 0 if hit else n
        print(f"  category id {cid!r}: seen on {n} order-item rows -- {'MATCHES a known product_categories row' if hit else 'NO MATCH in product_categories'}")
    print(f"\nTotal order-item rows with a category id that MATCHES product_categories: {matched}")
    print(f"Total order-item rows with a category id that does NOT match product_categories: {unmatched}")

    # ── Part 3: does dispensed_items' dollar total plausibly cover "all billed
    # items", or mostly just inventory-tracked products? Compare against
    # salesReport's revenue for the exact same window/location. ──
    sales_result = gql(token, SALES_QUERY, {"lids": [LOCATION_ID], "s": s_str, "e": e_str})
    sales_rows = (sales_result.get("data") or {}).get("salesReport") or []
    sales_total = sum(float(r.get("total") or 0) for r in sales_rows) if isinstance(sales_rows, list) else None
    usage_total = total_subtotal_cents / 100.0
    print(f"\n--- Revenue coverage check, same window/location ---")
    print(f"usageReport.orderItems subtotalCents sum: ${usage_total:,.2f}")
    print(f"salesReport revenue total:                {'$' + format(sales_total, ',.2f') if sales_total is not None else '(could not compute -- see errors below)'}")
    if "errors" in sales_result:
        print("salesReport errors:", json.dumps(sales_result["errors"])[:500])
    if sales_total:
        print(f"Coverage: {usage_total / sales_total * 100:.1f}% of salesReport revenue is represented in usageReport.orderItems")


if __name__ == "__main__":
    main()
