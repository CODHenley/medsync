#!/usr/bin/env python3
"""
scoutsync_check_month_truncation.py
Root-cause hunt for why dispensed_items_backfill.py's full-history
re-runs never fix historical rows even though:
  - Vetspire's product(id) query shows the correct current category
  - The exact SAME usageReport field, queried narrow (3 days, 1 location),
    also shows the correct current category
  - A fresh full-history backfill (Jan 1 - today) just ran successfully
    and changed almost nothing for "Exam - Urgent Care" (523783)

dispensed_items_backfill.py queries usageReport in FULL CALENDAR MONTH
chunks per location (see month_chunks() + backfill_location() in that
script) -- much wider than the 3-day test that worked. Hypothesis:
Vetspire's usageReport silently truncates the orderItems list for large
date ranges / high-volume locations, so most historical order items for
a busy month + a very-high-volume product (Exam - Urgent Care, the
single highest-volume item overall) never even come back in the
response -- meaning the backfill never gets a chance to update them,
regardless of how many times it's re-run.

This replays the EXACT query shape dispensed_items_backfill.py uses for
August 2026 @ Lincoln Park (the location+month covering the "most recent
uncategorized dispensed_at" we found: 2026-08-22) and checks:
  1. How many total order items come back.
  2. Whether product_id 523783 appears at all, and how many times.
  3. Whether the count looks suspiciously round (a truncation limit).

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, os, urllib.request, urllib.error
from collections import Counter

VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

LOCATION_ID = "23083"  # Lincoln Park
MONTH_START = "2026-08-01"
MONTH_END = "2026-08-31"

TARGET_PRODUCT_ID = "523783"  # Exam - Urgent Care

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            productId
            product { id name productCategories { id name } }
            updatedAt
        }
    }
}
"""


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
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:400]}"}]}


def main():
    token = load_token()
    print(f"=== Replaying dispensed_items_backfill.py's exact query shape: {MONTH_START}..{MONTH_END} @ location {LOCATION_ID} ===\n")

    result = gql(token, USAGE_QUERY, {"lids": [LOCATION_ID], "s": MONTH_START, "e": MONTH_END})
    if "errors" in result:
        print(f"ERROR: {result['errors']}")
        return

    items = (result.get("data") or {}).get("usageReport", {}).get("orderItems") or []
    print(f"Total order items returned: {len(items)}")

    ids = [it.get("id") for it in items]
    dup_count = len(ids) - len(set(ids))
    print(f"Duplicate order_item_ids in response: {dup_count}")

    target_matches = [it for it in items if str(it.get("productId")) == TARGET_PRODUCT_ID]
    print(f"\nOrder items matching product_id={TARGET_PRODUCT_ID} (Exam - Urgent Care): {len(target_matches)}")
    for it in target_matches[:5]:
        prod = it.get("product") or {}
        print(f"  order_item_id={it.get('id')} updatedAt={it.get('updatedAt')} productCategories={prod.get('productCategories')}")

    # Breakdown by product to see if this is a general truncation (would
    # show suspiciously low per-product counts across the board) vs.
    # something specific to this one product.
    by_product = Counter(str(it.get("productId")) for it in items)
    print(f"\nDistinct products in this month's response: {len(by_product)}")
    print("Top 10 products by order-item count in this response:")
    for pid, cnt in by_product.most_common(10):
        print(f"  product_id={pid}: {cnt}")


if __name__ == "__main__":
    main()
