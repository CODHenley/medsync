#!/usr/bin/env python3
"""
Usage-Based Min/Max Sync
------------------------
Reads dispensed_items from Supabase (populated nightly by wheaton_usage_pull.py),
calculates seasonal average daily usage per product, then:
  - Updates products.qty_min and products.qty_max in Supabase
  - Pushes minimumThreshold / reorderQuantity to Vetspire for all 4 locations

Equations:
  Peak season : May – September (months 5–9)
  qty_min     = ceil(14 × avg_daily_usage_current_season)
  qty_max     = ceil(30 × avg_daily_usage_peak_season)

Run: python3 usage_minmax_sync.py [--dry-run]
GitHub Actions: daily at midnight CT (06:00 UTC)
"""

import json, math, os, sys, urllib.request, urllib.error, urllib.parse, argparse
from datetime import date, timedelta
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = os.environ.get("SUPA_SERVICE_KEY") or os.environ.get("SUPA_ANON_KEY", (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iL"
    "CJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
    ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
))

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

# All Scout Care locations
LOCATION_IDS = ["28250", "28251", "28252", "28253"]

PEAK_MONTHS = {5, 6, 7, 8, 9}  # May – September


# ── Season helpers ────────────────────────────────────────────────────────────
def is_peak(d: date) -> bool:
    return d.month in PEAK_MONTHS


def date_range_days(start: date, end: date) -> list[date]:
    """Inclusive list of dates from start to end."""
    delta = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(delta)]


# ── Supabase helpers ──────────────────────────────────────────────────────────
def supa_get(path: str) -> list:
    req = urllib.request.Request(
        SUPA_URL + path,
        headers={
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def supa_patch(path: str, body: dict) -> bool:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        SUPA_URL + path,
        data=data,
        method="PATCH",
        headers={
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status < 300
    except urllib.error.HTTPError as e:
        print(f"    Supabase PATCH error {e.code}: {e.read().decode()[:200]}")
        return False


# ── Vetspire helpers ──────────────────────────────────────────────────────────
def gql(token: str, query: str, variables: dict = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
            "Origin": VETSPIRE_ORIGIN,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


UPSERT_MUTATION = """
mutation upsertLowStockThreshold($input: LowStockThresholdInput!) {
  upsertLowStockThreshold(input: $input) {
    id
    locationId
    threshold
    reorderQuantity
    __typename
  }
}
"""


def push_vetspire_threshold(token: str, location_id: str, product_id: str,
                             qty_min: int, qty_max: int, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY-RUN] VetSpire loc={location_id} prod={product_id} "
              f"min={qty_min} max={qty_max}")
        return True
    try:
        result = gql(token, UPSERT_MUTATION, {"input": {
            "locationId":      str(location_id),
            "productId":       str(product_id),
            "threshold":       qty_min,
            "reorderQuantity": qty_max,
        }})
        if "errors" in result:
            print(f"    VetSpire error: {result['errors'][0]['message'][:200]}")
            return False
        return True
    except Exception as e:
        print(f"    VetSpire exception: {e}")
        return False


# ── Usage calculation ─────────────────────────────────────────────────────────
def fetch_dispensed_items() -> list:
    """
    Fetch all dispensed_items rows that join to a product in our products table.
    We pull the vetspire_product_id and dispensed_at date, plus quantity.
    Returns: list of {vetspire_product_id, dispensed_date (date obj), quantity}
    """
    items = []
    page_size = 1000
    offset = 0

    while True:
        rows = supa_get(
            f"/rest/v1/dispensed_items"
            f"?select=vetspire_product_id,quantity,dispensed_at"
            f"&returned=eq.false&refunded=eq.false"
            f"&order=dispensed_at.asc"
            f"&limit={page_size}&offset={offset}"
        )
        if not rows:
            break
        for row in rows:
            vid = row.get("vetspire_product_id")
            qty = row.get("quantity") or 0
            da  = row.get("dispensed_at", "")[:10]  # YYYY-MM-DD
            if vid and qty and da:
                try:
                    items.append({
                        "vetspire_product_id": str(vid),
                        "dispensed_date": date.fromisoformat(da),
                        "quantity": float(qty),
                    })
                except ValueError:
                    pass
        if len(rows) < page_size:
            break
        offset += page_size

    return items


def compute_avg_daily(items: list, peak_only: bool) -> dict[str, float]:
    """
    Given dispensed_items rows, return a mapping of vetspire_product_id → avg daily usage.
    peak_only=True  → restrict to May-Sept dates only
    peak_only=False → use all dates (current season only, caller decides)
    """
    # Sum qty per product per date
    daily: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for item in items:
        d = item["dispensed_date"]
        if peak_only and not is_peak(d):
            continue
        daily[item["vetspire_product_id"]][d] += item["quantity"]

    # Count unique days in the relevant period, then average
    result = {}
    for vid, day_map in daily.items():
        if not day_map:
            continue
        # Number of unique calendar days with any dispensing in this window
        all_days = sorted(day_map.keys())
        span_days = (all_days[-1] - all_days[0]).days + 1
        # Use calendar span so zero-usage days pull the average down realistically
        total_qty = sum(day_map.values())
        result[vid] = total_qty / max(span_days, 1)

    return result


def fetch_tracked_products() -> list:
    """
    Return products table rows that have a vetspire_product_id set.
    Fields: id, name, vetspire_product_id, qty_min, qty_max
    """
    return supa_get(
        "/rest/v1/products"
        "?select=id,name,vetspire_product_id,qty_min,qty_max"
        "&vetspire_product_id=not.is.null"
        "&order=name.asc"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Update min/max from Vetspire usage data")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: VETSPIRE_API_TOKEN env var required")
        sys.exit(1)

    today       = date.today()
    peak_now    = is_peak(today)
    season_name = "PEAK (May–Sept)" if peak_now else "OFF-PEAK (Oct–Apr)"
    print(f"\n=== Usage Min/Max Sync — {today} | Season: {season_name} ===")
    print(f"Dry run: {args.dry_run}\n")

    # 1. Fetch all dispensed history
    print("Fetching dispensed_items from Supabase…")
    all_items = fetch_dispensed_items()
    print(f"  {len(all_items):,} dispensed rows loaded")
    if not all_items:
        print("No dispensed data found. Exiting.")
        sys.exit(0)

    # 2. Compute averages
    print("Computing seasonal averages…")
    peak_avg   = compute_avg_daily(all_items, peak_only=True)
    all_avg    = compute_avg_daily(all_items, peak_only=False)
    current_avg = peak_avg if peak_now else {
        vid: v for vid, v in all_avg.items()
        if vid not in peak_avg or True  # include all, off-peak = all-time
    }
    # For off-peak current, recompute using only off-peak dates
    if not peak_now:
        current_avg = compute_avg_daily(
            [i for i in all_items if not is_peak(i["dispensed_date"])],
            peak_only=False,
        )

    # 3. Fetch tracked products
    print("Fetching tracked products from Supabase…")
    products = fetch_tracked_products()
    print(f"  {len(products)} tracked products with VetSpire IDs\n")

    ok = 0
    skip = 0
    fail = 0

    for prod in products:
        vid  = str(prod["vetspire_product_id"])
        name = prod["name"]

        curr_daily = current_avg.get(vid, 0.0)
        peak_daily = peak_avg.get(vid, curr_daily)  # fall back to current if no peak data

        if curr_daily == 0.0 and peak_daily == 0.0:
            print(f"  SKIP {name} — no dispensed history")
            skip += 1
            continue

        qty_min = max(1, math.ceil(14 * curr_daily))
        qty_max = max(qty_min + 1, math.ceil(30 * peak_daily))

        print(f"  {name}")
        print(f"    current avg/day={curr_daily:.3f}  peak avg/day={peak_daily:.3f}")
        print(f"    qty_min={qty_min}  qty_max={qty_max}")

        # 4a. Update Supabase products table
        if args.dry_run:
            print(f"    [DRY-RUN] Would patch products id={prod['id']}")
        else:
            success = supa_patch(
                f"/rest/v1/products?id=eq.{prod['id']}",
                {"qty_min": qty_min, "qty_max": qty_max},
            )
            if not success:
                print(f"    ✗ Supabase patch failed")
                fail += 1
                continue
            print(f"    ✓ Supabase updated")

        # 4b. Push to VetSpire for all locations
        vs_ok = 0
        for loc_id in LOCATION_IDS:
            pushed = push_vetspire_threshold(
                token, loc_id, vid, qty_min, qty_max, args.dry_run
            )
            if pushed:
                vs_ok += 1

        if vs_ok == len(LOCATION_IDS):
            print(f"    ✓ VetSpire updated ({vs_ok}/{len(LOCATION_IDS)} locations)")
            ok += 1
        else:
            print(f"    ⚠ VetSpire partial ({vs_ok}/{len(LOCATION_IDS)} locations)")
            ok += 1  # Supabase succeeded; count partial VS as best-effort

    print(f"\nDone. {ok} updated, {skip} skipped (no history), {fail} failed.\n")


if __name__ == "__main__":
    main()
