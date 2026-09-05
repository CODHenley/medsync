#!/usr/bin/env python3
"""
vetspire_financial_category_investigation.py
Investigates the large "Uncategorized" bucket in the dashboard's Revenue by
Source chart -- that chart is built from invoice_line_items (populated by
vetspire_financial_sync.py from Vetspire's salesReport, breakdowns:
[PROVIDER_ID, PRODUCT_CATEGORY_ID]), which is a COMPLETELY SEPARATE
categorization pipeline from dispensed_items (populated by
vetspire_intraday_sync.py / dispensed_items_backfill.py from Vetspire's
usageReport, product.productCategories). The category-0 fix earlier this
session (full-history backfill + manual Vetspire recategorization, rounds
1-3) only ever touched dispensed_items -- it never touched this one.

salesReport is pre-aggregated (day/provider/category totals, no per-line
product detail), so getting to specific product names requires re-querying
with breakdowns:[PRODUCT_ID, PRODUCT_CATEGORY_ID] instead, then checking
whether Vetspire exposes any way to resolve a bare product_id to a name.

Also cross-checks the top uncategorized product_ids found here against
dispensed_items.product_category_id for the same vetspire_product_id, to
tell apart two very different explanations:
  (a) same root cause -- these are the same still-uncategorized-in-Vetspire
      products from the earlier investigation's unfinished round 3, just
      showing up in a second pipeline that was never examined before, or
  (b) a genuinely separate/new gap specific to how salesReport assigns
      product_category_id.

Report-only. No Supabase writes. Delete once its purpose is served, per
this repo's convention for one-off diagnostics.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_financial_category_investigation.py --days 90
"""
import argparse, json, os, time, urllib.request, urllib.error
from datetime import date, timedelta

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "23083": "Lincoln Park",
    "27390": "Old Orchard",
    "24356": "West Loop",
    "28253": "Wheaton",
}

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


def _urlopen_with_retry(req, timeout):
    last_err = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"    transient error ({last_err}) -- retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            time.sleep(wait)
    raise last_err


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": token,
    })
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        body, _ = _urlopen_with_retry(req, timeout=30)
        page = json.loads(body)
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip()
    return token.removeprefix("Bearer ").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="Trailing window in days")
    args = ap.parse_args()

    token = load_token()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    end = date.today()
    start = end - timedelta(days=args.days)
    print(f"=== Revenue by Source 'Uncategorized' investigation: trailing {args.days} days ({start} → {end}) ===\n")

    # 1. Root query fields matching "product" -- is there any way to resolve
    # a bare product_id (from salesReport's PRODUCT_ID breakdown) to a name?
    print("=== Root query fields matching 'product' ===")
    r = gql(token, "{ __schema { queryType { fields { name description } } } }")
    fields = (r.get("data") or {}).get("__schema", {}).get("queryType", {}).get("fields", [])
    product_fields = [f for f in fields if "product" in f.get("name", "").lower()]
    for f in product_fields:
        print(f"  * {f['name']}: {f.get('description', '')}")
    if not product_fields:
        print("  (none)")
    print()

    # 2. salesReport re-queried with breakdowns:[PRODUCT_ID, PRODUCT_CATEGORY_ID]
    # instead of PROVIDER_ID -- same underlying report vetspire_financial_sync.py
    # already uses, just a different breakdown combination, so this is confirmed
    # to be a legal call, not a guess.
    revenue_by_product = {}
    total_all = 0.0
    total_uncategorized = 0.0
    sample_null_product_rows = []
    for vetspire_loc_id, loc_name in LOCATIONS.items():
        query = """
        query($lids:[ID!], $s:Date, $e:Date){
            salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                        breakdowns:[PRODUCT_ID, PRODUCT_CATEGORY_ID], segment:DAY)
        }
        """
        r = gql(token, query, {"lids": [vetspire_loc_id], "s": start.isoformat(), "e": end.isoformat()})
        if "errors" in r:
            print(f"  ERROR ({loc_name}): {r['errors']}")
            continue
        raw = r.get("data", {}).get("salesReport", "[]")
        rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
        print(f"  {loc_name}: {len(rows)} rows")
        for row in rows:
            total = float(row.get("total") or 0)
            total_all += total
            cat_id = row.get("product_category_id")
            if cat_id is None or cat_id == 0:
                total_uncategorized += total
                pid = row.get("product_id")
                revenue_by_product[pid] = revenue_by_product.get(pid, 0.0) + total
                if pid is None and len(sample_null_product_rows) < 10:
                    sample_null_product_rows.append(row)
    print()

    # 2b. The dominant uncategorized revenue has product_id=None entirely --
    # not a mis-tagged product, something salesReport can't attribute to any
    # product record at all. Print the raw row dicts (not just the fields
    # this script has been extracting) in case salesReport already returns
    # other identifying fields for this breakdown that were never examined.
    print("=== Raw row dicts for a sample of product_id=None, uncategorized rows ===")
    for row in sample_null_product_rows:
        print(f"  {row}")
    if not sample_null_product_rows:
        print("  (none found)")
    print()

    # 2c. Characterize the product_id=None cohort along other dimensions --
    # re-querying with REVENUE_CENTER_ID / DEPARTMENT_ID / PRODUCT_TYPE_ID
    # paired with PRODUCT_CATEGORY_ID (kept in every combo so the
    # "uncategorized" filter still applies) to see if this revenue
    # concentrates under a specific revenue center, department, or product
    # type even though it has no specific product attached.
    dim_top_values = {}
    for dim in ("REVENUE_CENTER_ID", "DEPARTMENT_ID", "PRODUCT_TYPE_ID"):
        field_name = dim.lower()  # e.g. revenue_center_id
        print(f"=== Uncategorized revenue by {dim} ===")
        by_dim = {}
        for vetspire_loc_id, loc_name in LOCATIONS.items():
            query = f"""
            query($lids:[ID!], $s:Date, $e:Date){{
                salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                            breakdowns:[{dim}, PRODUCT_CATEGORY_ID], segment:DAY)
            }}
            """
            r = gql(token, query, {"lids": [vetspire_loc_id], "s": start.isoformat(), "e": end.isoformat()})
            if "errors" in r:
                print(f"  ERROR ({loc_name}): {r['errors']}")
                continue
            raw = r.get("data", {}).get("salesReport", "[]")
            rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
            for row in rows:
                cat_id = row.get("product_category_id")
                if cat_id is None or cat_id == 0:
                    total = float(row.get("total") or 0)
                    key = row.get(field_name)
                    by_dim[key] = by_dim.get(key, 0.0) + total
        top_vals = sorted(by_dim.items(), key=lambda kv: kv[1], reverse=True)[:10]
        for key, total in top_vals:
            print(f"  {field_name}={key!r}: ${total:,.2f}")
        if not by_dim:
            print("  (no rows)")
        dim_top_values[dim] = top_vals
        print()

    # 2d. Try to resolve names for the top values in each dimension, using
    # whatever root query field matches its vocabulary (discovered live,
    # never assumed) -- same pattern as the product-name resolution below.
    for dim, keyword in (("REVENUE_CENTER_ID", "revenue"), ("DEPARTMENT_ID", "department"), ("PRODUCT_TYPE_ID", "producttype")):
        print(f"=== Root query fields matching {keyword!r} (for {dim} name resolution) ===")
        matches = [f for f in fields if keyword.replace("producttype", "product") in f.get("name", "").lower()
                   and ("type" in f.get("name", "").lower() if keyword == "producttype" else True)]
        for f in matches:
            print(f"  * {f['name']}: {f.get('description', '')}")
        if not matches:
            print("  (none)")
        candidate = next((f["name"] for f in matches if f["name"].lower() in
                           ("revenuecenter", "revenuecenters", "department", "departments", "producttype", "producttypes")), None)
        if candidate:
            print(f"  Attempting resolution via '{candidate}' for top {dim} values:")
            for key, total in dim_top_values.get(dim, []):
                if key is None:
                    continue
                q = f'{{ {candidate}(id: "{key}") {{ id name }} }}'
                rr = gql(token, q)
                if "errors" in rr:
                    print(f"    {key}: ERROR {rr['errors']}")
                else:
                    print(f"    {key}: {rr.get('data')}")
        print()
    print(f"  Total revenue (all categories, PRODUCT_ID breakdown): ${total_all:,.2f}")
    print(f"  Total uncategorized revenue (this breakdown):         ${total_uncategorized:,.2f}")
    print()

    top_products = sorted(revenue_by_product.items(), key=lambda kv: kv[1], reverse=True)[:25]
    print("=== Top uncategorized product_ids by revenue ===")
    for pid, rev in top_products:
        print(f"  product_id={pid!r}: ${rev:,.2f}")
    print()

    # 3. Try to resolve names for those product_ids, if a suitable root field
    # was found in step 1 (never assume the field/arg shape -- try the most
    # likely candidate and report the raw error if it's wrong rather than
    # silently skipping).
    if product_fields:
        candidate = next((f["name"] for f in product_fields if f["name"].lower() in ("product", "products")), None)
        if candidate:
            print(f"=== Attempting to resolve product names via '{candidate}' ===")
            for pid, rev in top_products[:15]:
                if not pid:
                    continue
                q = f'{{ {candidate}(id: "{pid}") {{ id name }} }}' if candidate == "product" else \
                    f'{{ {candidate}(ids: ["{pid}"]) {{ id name }} }}'
                rr = gql(token, q)
                if "errors" in rr:
                    print(f"  product_id={pid}: ERROR {rr['errors']}")
                else:
                    print(f"  product_id={pid}: {rr.get('data')}")
            print()

    # 4. Cross-check: for these same product_ids, what does dispensed_items
    # (the OTHER categorization pipeline, already investigated/fixed earlier)
    # currently show for product_category_id? Same-cause vs. separate-cause.
    print("=== Cross-check against dispensed_items.product_category_id (Supabase) ===")
    uncategorized_product_ids = {str(pid) for pid, _ in top_products if pid}
    if uncategorized_product_ids:
        di_rows = supa_get_all(
            "dispensed_items",
            "select=vetspire_product_id,product_name,product_category_id&"
            f"vetspire_product_id=in.({','.join(uncategorized_product_ids)})",
        )
        seen = {}
        for row in di_rows:
            pid = row.get("vetspire_product_id")
            seen.setdefault(pid, row)
        for pid in uncategorized_product_ids:
            row = seen.get(pid)
            if row:
                print(f"  product_id={pid}: dispensed_items shows product_category_id="
                      f"{row.get('product_category_id')!r}, name={row.get('product_name')!r}")
            else:
                print(f"  product_id={pid}: not found in dispensed_items at all")
    else:
        print("  (no uncategorized product_ids to cross-check)")
    print()

    print("=== Done ===")


if __name__ == "__main__":
    main()
