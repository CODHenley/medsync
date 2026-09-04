#!/usr/bin/env python3
"""
scoutsync_check_523783_live.py
Round 3 diagnostic (part 2): Supabase's dispensed_items still shows
product 523783 ("Exam - Urgent Care") uncategorized for 8833 historical
rows even after two full-history dispensed_items_backfill.py re-runs
since round 1 supposedly fixed it in Vetspire.

dispensed_items_backfill.py gets its category from usageReport's embedded
`product { productCategories { id name } }` field -- NOT from a direct
product(id) lookup. If that embedded field doesn't reflect live state the
way the direct product(id) query does, backfills would never pick up the
fix no matter how many times they're re-run. This checks both paths for
product 523783 (should now be "Service") and, as a control, product
524011 "Ultrasound Guided - Cystocentesis" (round 2, also fixed to
"Service", and confirmed as a residual few rows in earlier probes).

Read-only Vetspire GraphQL calls. Deleted once its purpose is served, per
this repo's convention.
"""
import json, os, sys, urllib.request, urllib.error

VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

CHECK_IDS = {
    "523783": "Exam - Urgent Care (round 1)",
    "524011": "Ultrasound Guided - Cystocentesis (round 2)",
}

# A location + narrow date window to probe usageReport's embedded category
# field. Lincoln Park, a few recent days.
LOCATION_ID = "23083"  # Lincoln Park
USAGE_START = "2026-08-20"
USAGE_END = "2026-08-22"


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set.")
    return token.removeprefix("Bearer ").strip()


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
            "Origin": VETSPIRE_ORIGIN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:300]}"}]}


def main():
    token = load_token()

    print("=== Part A: direct product(id) query (the source of truth we wrote to) ===\n")
    for pid, label in CHECK_IDS.items():
        result = gql(
            token,
            "query($id: ID) { product(id: $id) { id name productCategories { id name } } }",
            {"id": pid},
        )
        print(f"product {pid} ({label}):")
        print(f"  {json.dumps(result)}\n")

    print(f"\n=== Part B: usageReport embedded product.productCategories, {USAGE_START}..{USAGE_END} @ location {LOCATION_ID} ===\n")
    result = gql(
        token,
        """
        query($lids:[ID!], $s:Date, $e:Date){
            usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
                orderItems {
                    id
                    productId
                    product { id name productCategories { id name } }
                }
            }
        }
        """,
        {"lids": [LOCATION_ID], "s": USAGE_START, "e": USAGE_END},
    )
    if "errors" in result:
        print(f"  ERROR: {result['errors']}")
        return

    items = (result.get("data") or {}).get("usageReport", {}).get("orderItems") or []
    print(f"  {len(items)} order items in window")

    matches = [it for it in items if str(it.get("productId")) in CHECK_IDS]
    print(f"  {len(matches)} order items matching our two watched product ids\n")
    for it in matches[:10]:
        prod = it.get("product") or {}
        print(f"    order_item_id={it.get('id')} productId={it.get('productId')} "
              f"name={prod.get('name')!r} productCategories={prod.get('productCategories')}")

    # Also show a handful of ANY order items' embedded categories, to see if
    # the field is populated at all for other (definitely-categorized)
    # products in this same response -- tells us if this is a
    # usageReport-wide resolver gap or specific to these two products.
    print("\n  -- sample of first 10 order items' embedded productCategories (any product) --")
    for it in items[:10]:
        prod = it.get("product") or {}
        print(f"    productId={it.get('productId')} name={prod.get('name')!r} "
              f"productCategories={prod.get('productCategories')}")


if __name__ == "__main__":
    main()
