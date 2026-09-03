#!/usr/bin/env python3
"""
scoutsync_category_writeback_test.py
Single-item, user-authorized test: does our Vetspire API token actually
have write access to updateProductProductCategory (confirmed to exist in
the schema via scoutsync_uncategorized_services_probe.py, but never
called)? Schema presence doesn't guarantee our token's write scope
matches its read scope -- this has never been tested.

Chosen test product deliberately for low blast radius: "Radiology -
Radiography Interpretation (7-11)" is an unambiguous match for the
existing "Radiology" category (id 13598) -- genuinely correct if it
works, not junk data -- modest volume (17 orders/90 days), and trivially
reversible afterward (same mutation, or by hand in Vetspire's own product
editor) if anything looks wrong.

Steps, each printed in full so the outcome is unambiguous either way:
  1. Introspect updateProductProductCategory's exact return type (never
     checked before -- only its name/args were introspected previously).
  2. Introspect the Query root for a way to read a single product back by
     id, so "the mutation returned 200" can't be mistaken for "the write
     actually persisted."
  3. Look up the target product's real Vetspire id from dispensed_items
     (synced from real order items -- no guessing an id).
  4. Read its category BEFORE the write.
  5. Call the mutation.
  6. Read its category AFTER the write, via the query path found in step 2
     -- a fresh read, not just trusting the mutation's own response.

Read-only until step 5. This is a single, deliberate, user-authorized
write test, not a general-purpose tool -- the target is hardcoded.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_category_writeback_test.py
"""
import json, os, urllib.parse, urllib.request, urllib.error

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

TARGET_CATEGORY_ID = "13598"  # Radiology, confirmed present in product_categories
PRODUCT_NAME_FILTER = "*Radiography Interpretation*"

MUTATION_RETURN_TYPE_QUERY = """
{
  __schema {
    mutationType {
      fields(includeDeprecated: true) {
        name
        type { kind name ofType { kind name ofType { kind name } } }
      }
    }
  }
}
"""

QUERY_ROOT_PRODUCT_FIELDS_QUERY = """
{
  __schema {
    queryType {
      fields {
        name
        args { name type { kind name ofType { kind name } } }
        type { kind name ofType { kind name } }
      }
    }
  }
}
"""


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": token,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:800]}")
        return {"errors": [{"message": f"HTTP {e.code}: {body[:500]}"}]}


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

    print("=== Step 1: updateProductProductCategory's real return type ===\n")
    mres = gql(token, MUTATION_RETURN_TYPE_QUERY)
    if "errors" in mres:
        print("Could not introspect mutation return type:", json.dumps(mres["errors"])[:800])
        return
    mfields = ((mres.get("data") or {}).get("__schema") or {}).get("mutationType", {}).get("fields") or []
    target_mutation = next((f for f in mfields if f["name"] == "updateProductProductCategory"), None)
    if not target_mutation:
        print("updateProductProductCategory not found in the live schema anymore -- aborting, nothing changed.")
        return
    print("updateProductProductCategory returns:", json.dumps(target_mutation["type"], indent=2))

    print("\n=== Step 2: find a Query root field to read a single product back ===\n")
    qres = gql(token, QUERY_ROOT_PRODUCT_FIELDS_QUERY)
    qfields = ((qres.get("data") or {}).get("__schema") or {}).get("queryType", {}).get("fields") or []
    product_query_candidates = [f for f in qfields if f["name"].lower() in ("product", "products")]
    for f in product_query_candidates:
        print(f"  {f['name']}: args={[a['name'] for a in f.get('args') or []]}, "
              f"returns={json.dumps(f['type'])}")
    if not product_query_candidates:
        print("No obvious single-product read field found -- printing all query fields containing 'product':")
        for f in qfields:
            if "product" in f["name"].lower():
                print(f"  {f['name']}")
        print("\nCannot safely verify a write without a confirmed read-back path -- aborting before any write.")
        return

    print("\n=== Step 3: look up the target product's real Vetspire id ===\n")
    rows = supa_get(
        "dispensed_items",
        f"select=vetspire_product_id,product_name&product_name=ilike.{urllib.parse.quote(PRODUCT_NAME_FILTER)}&limit=3",
    )
    if not rows:
        print(f"No dispensed_items row matched {PRODUCT_NAME_FILTER!r} -- aborting, nothing changed.")
        return
    product_id = rows[0]["vetspire_product_id"]
    print(f"Target: {rows[0]['product_name']!r} -- Vetspire product id {product_id}")
    print(f"(other matches seen: {[r['product_name'] for r in rows[1:]]})")

    # Use whichever field step 2 found -- try "product(id: ID)" shape first (the
    # common Vetspire singular-query convention already confirmed for other
    # types like Order in this repo), falling back to "products(ids: [ID])".
    single_product_field = next((f for f in product_query_candidates if f["name"] == "product"), None)
    plural_product_field = next((f for f in product_query_candidates if f["name"] == "products"), None)

    def read_product_category():
        if single_product_field:
            q = "query($id: ID) { product(id: $id) { id name productCategories { id name } } }"
            r = gql(token, q, {"id": product_id})
            if "errors" not in r:
                return ((r.get("data") or {}).get("product") or {})
            print("  product(id:) query errored:", json.dumps(r["errors"])[:500])
        if plural_product_field:
            q = "query($ids: [ID]) { products(ids: $ids) { id name productCategories { id name } } }"
            r = gql(token, q, {"ids": [product_id]})
            if "errors" not in r:
                ps = (r.get("data") or {}).get("products") or []
                return ps[0] if ps else {}
            print("  products(ids:) query errored:", json.dumps(r["errors"])[:500])
        return None

    print("\n=== Step 4: category BEFORE the write ===\n")
    before = read_product_category()
    if before is None:
        print("Could not read the product back at all -- aborting before any write.")
        return
    print(json.dumps(before, indent=2))

    print("\n=== Step 5: calling updateProductProductCategory ===\n")
    mutation = """
    mutation($productId: ID, $categoryId: ID) {
      updateProductProductCategory(productId: $productId, productCategoryId: $categoryId) {
        id
      }
    }
    """
    write_result = gql(token, mutation, {"productId": product_id, "categoryId": TARGET_CATEGORY_ID})
    print(json.dumps(write_result, indent=2))

    print("\n=== Step 6: category AFTER the write (fresh read, not trusting the mutation's own response) ===\n")
    after = read_product_category()
    print(json.dumps(after, indent=2) if after is not None else "Could not re-read the product.")

    print("\n=== RESULT ===")
    print(f"BEFORE: {before.get('productCategories') if before else '(unreadable)'}")
    print(f"AFTER:  {after.get('productCategories') if after else '(unreadable)'}")
    if after and after.get("productCategories") and any(
        str(c.get("id")) == TARGET_CATEGORY_ID for c in after["productCategories"]
    ):
        print("WRITE CONFIRMED -- the category change actually persisted.")
    else:
        print("NO CHANGE DETECTED -- either the mutation errored, or our token lacks write access despite the "
              "mutation being present in the schema, or the return/read shape assumed above doesn't match reality.")


if __name__ == "__main__":
    main()
