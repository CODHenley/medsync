#!/usr/bin/env python3
"""
MedSync — Dispensed Items Backfill
Pulls historical usageReport from Vetspire for all 4 Scout locations
and upserts to Supabase dispensed_items table.

Covers any date range; default is 2026-01-01 → 2026-04-30 (the gap
before the nightly sync started in May 2026).

NOTE: Unlike the old wheaton_usage_backfill.py, this script does NOT
skip items without a SKU — services, diagnostics, and everything else
billed on an invoice is included so COGS and Items Dispensed are complete.

Usage:
  python3 dispensed_items_backfill.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--location NAME] [--dry-run]
  VETSPIRE_API_TOKEN="..." python3 dispensed_items_backfill.py --start 2026-01-01 --end 2026-04-30
"""

import argparse, json, urllib.request, urllib.error, os
from datetime import date, datetime, timezone, timedelta

VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
SUPA_URL          = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY          = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

DEFAULT_START = "2026-01-01"
DEFAULT_END   = "2026-04-30"

ALL_LOCATIONS = [
    ("Lincoln Park", "23083"),
    ("Old Orchard",  "27390"),
    ("West Loop",    "24356"),
    ("Wheaton",      "28253"),
]

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
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
    for path in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetspire_token.txt"),
        os.path.expanduser("~/.vetspire_token"),
    ):
        if os.path.exists(path):
            return open(path).read().strip().removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set and no token file found.")


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_ENDPOINT, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
        "Origin":        "https://scoutcare.vetspire.com",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:200]}"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


def supa_upsert(records):
    if not records:
        return 201
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items?on_conflict=vetspire_product_id,dispensed_at,location_id",
        data=body,
        headers={
            "Content-Type":  "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "resolution=merge-duplicates,return=minimal",
        },
    )
    req.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print(f"    Supabase error {e.code}: {e.read().decode()[:200]}")
        return e.code


def month_chunks(start: date, end: date):
    """Yield (chunk_start, chunk_end) pairs broken at month boundaries."""
    cursor = start
    while cursor <= end:
        y, m = cursor.year, cursor.month
        if m == 12:
            next_month_start = date(y + 1, 1, 1)
        else:
            next_month_start = date(y, m + 1, 1)
        chunk_end = min(next_month_start - timedelta(days=1), end)
        yield cursor, chunk_end
        cursor = next_month_start


def backfill_location(token, loc_name, loc_id, start: date, end: date, dry_run: bool):
    print(f"\n📍 {loc_name} (ID: {loc_id})  {start} → {end}")
    print("   " + "-" * 50)

    total_upserted = 0
    total_skipped  = 0

    for chunk_start, chunk_end in month_chunks(start, end):
        s = chunk_start.isoformat()
        e = chunk_end.isoformat()
        print(f"   Pulling {s} → {e} ...", end=" ", flush=True)

        result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": s, "e": e})

        if "errors" in result:
            print(f"ERROR: {result['errors'][0]['message'][:100]}")
            continue

        order_items = (
            result.get("data", {})
                  .get("usageReport", {})
                  .get("orderItems", []) or []
        )
        print(f"{len(order_items)} items", end=" ")

        records = []
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            if not pid:
                total_skipped += 1
                continue

            updated_at = item.get("updatedAt") or datetime.now(timezone.utc).isoformat()
            if "+" not in updated_at and updated_at[-1] != "Z":
                updated_at += "Z"

            unit_cost  = prod.get("unitCost")
            unit_price = 0.0
            try:
                unit_price = float(item.get("unitPrice") or 0)
            except (ValueError, TypeError):
                pass

            records.append({
                "vetspire_product_id":    str(pid),
                "product_name":           prod.get("name") or "",
                "sku":                    prod.get("sku") or None,
                "quantity":               float(item.get("quantity") or 0),
                "quantity_remaining":     float(item.get("quantityRemaining") or 0),
                "unit_price":             unit_price,
                "unit_cost":              float(unit_cost) if unit_cost is not None else None,
                "subtotal_cents":         int(item.get("subtotalCents") or 0),
                "total_before_tax_cents": int(item.get("totalBeforeTaxCents") or 0),
                "returned":               bool(item.get("returned", False)),
                "refunded":               bool(item.get("refunded", False)),
                "dispensed_at":           updated_at,
                "location_id":            loc_id,
                "location_name":          loc_name,
                "pulled_at":              datetime.now(timezone.utc).isoformat(),
            })

        if dry_run:
            print(f"→ [DRY RUN] would upsert {len(records)}")
            total_upserted += len(records)
            continue

        if records:
            status = supa_upsert(records)
            if str(status).startswith("2"):
                print(f"→ ✓ upserted {len(records)}")
                total_upserted += len(records)
            else:
                print(f"→ ✗ failed (HTTP {status})")
        else:
            print("→ 0 records")

    print(f"   Total for {loc_name}: {total_upserted} upserted, {total_skipped} skipped (no productId)")
    return total_upserted


def main():
    parser = argparse.ArgumentParser(description="Backfill dispensed_items from Vetspire usageReport")
    parser.add_argument("--start",    default=DEFAULT_START, help=f"Start date YYYY-MM-DD (default {DEFAULT_START})")
    parser.add_argument("--end",      default=DEFAULT_END,   help=f"End date YYYY-MM-DD (default {DEFAULT_END})")
    parser.add_argument("--location", default=None, help="Single location name (default: all 4)")
    parser.add_argument("--dry-run",  action="store_true", help="Print counts without writing to Supabase")
    args = parser.parse_args()

    token = load_token()
    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)

    locations = [
        (name, lid) for name, lid in ALL_LOCATIONS
        if args.location is None or name.lower() == args.location.lower()
    ]
    if not locations:
        raise SystemExit(f"ERROR: no location matched '{args.location}'")

    print(f"\nMedSync — Dispensed Items Backfill")
    print(f"Range    : {start} → {end}")
    print(f"Locations: {', '.join(n for n, _ in locations)}")
    if args.dry_run:
        print("Mode     : DRY RUN (no writes)")
    print("=" * 60)

    grand_total = 0
    for loc_name, loc_id in locations:
        grand_total += backfill_location(token, loc_name, loc_id, start, end, args.dry_run)

    print(f"\n{'=' * 60}")
    print(f"Backfill complete — {grand_total} total rows upserted across {len(locations)} location(s)")
    print("Re-run any time; existing rows are merged (no duplicates).\n")


if __name__ == "__main__":
    main()
