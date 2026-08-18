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

One row per real Vetspire order item, keyed by (order_item_id, location_id)
— NOT aggregated by day/month/product. This is the single natural key every
dispensed_items writer in this repo uses (see vetspire_intraday_sync.py,
backfill_date_range.py, wheaton_usage_pull.py) specifically so that two
different scripts can never disagree on grouping and double-count the same
real event — that disagreement (day-level vs month-level aggregation) is
what caused the Aug 2026 double-count incident. Never reintroduce
aggregation here; if you need per-day/per-month totals, compute them with a
SQL view over these rows, not by pre-aggregating at write time. Re-running
this script for the same range is always safe/idempotent.

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
    conflict = "order_item_id,location_id"
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + f"/rest/v1/dispensed_items?on_conflict={conflict}",
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
    """Yield (month_start, month_end) pairs covering start→end, clamped to [start, end]."""
    import calendar
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        chunk_start = max(cursor, start)
        chunk_end   = min(date(cursor.year, cursor.month, last_day), end)
        yield chunk_start, chunk_end
        # advance to first day of next month
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def backfill_location(token, loc_name, loc_id, start: date, end: date, dry_run: bool):
    print(f"\n📍 {loc_name} (ID: {loc_id})  {start} → {end}")
    print("   " + "-" * 50)

    total_upserted = 0
    total_skipped  = 0
    total_errors   = 0

    for chunk_start, chunk_end in month_chunks(start, end):
        s = chunk_start.isoformat()
        e = chunk_end.isoformat()
        # Store all items in this chunk keyed to the first day of the month.
        # Using full-month ranges matches Vetspire's own report boundaries (CDT),
        # eliminating the UTC/CDT midnight drift that daily queries introduce.
        month_key = date(chunk_start.year, chunk_start.month, 1).isoformat() + "T00:00:00Z"
        print(f"   Pulling {s} → {e} ...", end=" ", flush=True)

        result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": s, "e": e})

        if "errors" in result:
            print(f"ERROR: {result['errors'][0]['message'][:100]}")
            total_errors += 1
            continue

        order_items = (
            result.get("data", {})
                  .get("usageReport", {})
                  .get("orderItems", []) or []
        )
        print(f"{len(order_items)} items", end=" ")

        # One row per real order item — no aggregation. order_item_id is the
        # sole natural key (see module docstring for why aggregation is banned
        # here).
        now_iso = datetime.now(timezone.utc).isoformat()
        records = []
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            oid  = item.get("id")
            if not pid or not oid:
                total_skipped += 1
                continue

            unit_cost  = prod.get("unitCost")
            unit_price = 0.0
            try:
                unit_price = float(item.get("unitPrice") or 0)
            except (ValueError, TypeError):
                pass

            updated_at = item.get("updatedAt")
            dispensed_at = updated_at if updated_at else month_key
            if dispensed_at and "T" in dispensed_at and not dispensed_at.endswith("Z") and "+" not in dispensed_at[10:]:
                dispensed_at += "Z"  # Vetspire returns naive datetimes — treat as UTC

            records.append({
                "order_item_id":          str(oid),
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
                "dispensed_at":           dispensed_at,
                "location_id":            loc_id,
                "location_name":          loc_name,
                "pulled_at":              now_iso,
            })

        if dry_run:
            print(f"→ [DRY RUN] would upsert {len(records)}")
            total_upserted += len(records)
            continue

        if records:
            chunk_ok = True
            for i in range(0, len(records), 500):
                status = supa_upsert(records[i:i + 500])
                if not str(status).startswith("2"):
                    chunk_ok = False
                    total_errors += 1
                else:
                    total_upserted += len(records[i:i + 500])
            print(f"→ {'✓ upserted' if chunk_ok else '✗ FAILED partway,'} {len(records)}")
        else:
            print("→ 0 items")

    print(f"   Total for {loc_name}: {total_upserted} upserted, {total_skipped} skipped (no product/item id), {total_errors} error(s)")
    return total_upserted, total_errors


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

    grand_total  = 0
    grand_errors = 0
    for loc_name, loc_id in locations:
        upserted, errors = backfill_location(token, loc_name, loc_id, start, end, args.dry_run)
        grand_total  += upserted
        grand_errors += errors

    print(f"\n{'=' * 60}")
    print(f"Backfill complete — {grand_total} total rows upserted across {len(locations)} location(s), {grand_errors} error(s)")
    print("Re-run any time; existing rows (by order_item_id) are merged, never duplicated.\n")
    if grand_errors and not args.dry_run:
        raise SystemExit(1)  # incomplete backfill — never report success on partial data


if __name__ == "__main__":
    main()
