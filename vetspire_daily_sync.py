#!/usr/bin/env python3
"""
MedSync — Vetspire Daily Usage Sync
-------------------------------------
Runs at midnight. For each location + product:

  1. Pulls current on-hand from Vetspire (getProductCounts + inventoryLevels)
  2. Stores a daily snapshot in Supabase (inventory_snapshots table)
  3. Calculates 30-day rolling average daily consumption from snapshots
     (accounts for restocks: only counts days where stock went DOWN)
  4. Applies seasonal adjustment factor (peak May–Oct vs off-peak)
  5. Calculates new Min = adjusted_daily × 3 days (lead time + safety buffer)
              new Max = adjusted_daily × 7 days (weekly order cycle)
  6. Writes updated thresholds back to Vetspire via upsertLowStockThreshold

Unit awareness:
  Vetspire stores on-hand in the unit of measure the product is sold in
  (tablets, mL, puffs, doses, etc). All calculations use that native unit
  unchanged — no conversion needed.

Requires:
  pip install requests --break-system-packages

Usage:
  python3 vetspire_daily_sync.py --token YOUR_VETSPIRE_TOKEN [--dry-run] [--location "Old Orchard"]

Setup:
  Run inventory_snapshots_migration.sql in Supabase before first use.
  Needs at least 7 days of snapshots before min/max writes are meaningful.
"""

import sys
import json
import math
import datetime
import argparse
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
VETSPIRE_URL = 'https://api.vetspire.com/graphql'
SUPA_URL     = 'https://aemkdummdrmxtwrkggjw.supabase.co'
SUPA_KEY     = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s'

# Vetspire location IDs (confirmed via GraphQL inspector)
LOCATIONS = {
    'Lincoln Park': '23083',
    'Old Orchard':  '27390',
    'West Loop':    '24356',
    'Wheaton':      '28253',
}

# Seasonal: peak = May–Oct (months 5–10), off-peak = Nov–Apr
PEAK_MONTHS    = {5, 6, 7, 8, 9, 10}
PEAK_FACTOR    = 1.25   # 25% higher demand in peak season
OFFPEAK_FACTOR = 0.85   # 15% lower demand in off-peak

# Min/Max calculation parameters
LEAD_TIME_DAYS  = 1    # MWI/Vetcove next-day delivery
SAFETY_DAYS     = 2    # buffer on top of lead time
ORDER_CYCLE_DAYS = 7   # weekly order cycle → Max covers one week
MIN_DAYS_DATA   = 7    # require at least 7 snapshots before writing

# ── Vetspire API ──────────────────────────────────────────────────────────────
def vs_gql(token, query, variables=None):
    """GraphQL call to Vetspire. Auth: Authorization: Bearer (confirmed via inspector)."""
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        headers={
            'Content-Type':  'application/json',
            'Authorization': token,   # API key — no Bearer prefix (confirmed via Vetspire support test)
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f'  Vetspire HTTP {e.code}: {body[:200]}')
        return {'errors': [{'message': f'HTTP {e.code}'}]}
    except Exception as e:
        print(f'  Vetspire request failed: {e}')
        return {'errors': [{'message': str(e)}]}


def get_products_at_location(token, location_id):
    """
    Paginated product list for one location.
    Returns list of dicts: { id, name, stock (summed across lots) }
    Confirmed query: getProductCounts with onlyTrackInventory + onlyEnabledAt.
    Stock is pulled via nested inventoryLevels(locationId).
    """
    all_products = []
    offset = 0
    page_size = 20

    # minimumThreshold + maximumQuantity are on LowStockThreshold, not Product
    # sortField/sortDirection are not used in getProductCounts operation — removed
    query = '''
    query getProductCounts(
      $locationId: ID!
      $limit: Int
      $offset: Int
    ) {
      products(
        onlyTrackInventory: true
        onlyEnabledAt: $locationId
        limit: $limit
        offset: $offset
      ) {
        id
        name
        inventoryLevels(locationId: $locationId) {
          stock
          locationId
        }
      }
    }'''

    while True:
        result = vs_gql(token, query, {
            'locationId': location_id,
            'limit':      page_size,
            'offset':     offset,
        })

        if 'errors' in result:
            print(f'  Error fetching products: {result["errors"]}')
            break

        page = result.get('data', {}).get('products', [])
        if not page:
            break

        for p in page:
            # Sum stock across all lots at this location
            levels = p.get('inventoryLevels') or []
            stock = sum(float(lv.get('stock') or 0) for lv in levels
                        if str(lv.get('locationId')) == str(location_id))
            all_products.append({
                'id':    p['id'],
                'name':  p['name'],
                'stock': stock,
            })

        if len(page) < page_size:
            break
        offset += page_size

    return all_products


def write_threshold(token, location_id, product_id, min_val, max_val, dry_run):
    """
    upsertLowStockThreshold — confirmed structure via GraphQL inspector.
    threshold      = Minimum Threshold (reorder point)
    reorderQuantity = Maximum Quantity (restocking target)
    Both values in Vetspire's native unit for this product.
    """
    min_int = max(1, int(math.ceil(min_val)))
    max_int = max(min_int + 1, int(math.ceil(max_val)))

    if dry_run:
        print(f'    [DRY RUN] min={min_int}  max={max_int}')
        return True

    mutation = '''
    mutation upsertLowStockThreshold($input: LowStockThresholdInput!) {
      upsertLowStockThreshold(input: $input) {
        id
        locationId
        threshold
        reorderQuantity
        __typename
      }
    }'''
    result = vs_gql(token, mutation, {'input': {
        'locationId':      str(location_id),
        'productId':       str(product_id),
        'threshold':       min_int,
        'reorderQuantity': max_int,
    }})
    return 'errors' not in result


# ── Supabase ──────────────────────────────────────────────────────────────────
def supa_request(method, path, body=None):
    """Supabase REST call."""
    url = SUPA_URL + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'apikey':        SUPA_KEY,
        'Authorization': 'Bearer ' + SUPA_KEY,
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        print(f'  Supabase {method} {path} → HTTP {e.code}: {e.read().decode()[:200]}')
        return None
    except Exception as e:
        print(f'  Supabase request failed: {e}')
        return None


def store_snapshot(vs_location_id, location_name, vs_product_id, product_name, stock):
    """Insert a daily on-hand snapshot into inventory_snapshots."""
    today = datetime.date.today().isoformat()
    supa_request('POST', '/rest/v1/inventory_snapshots', {
        'vetspire_location_id': vs_location_id,
        'location_name':        location_name,
        'vetspire_product_id':  vs_product_id,
        'product_name':         product_name,
        'on_hand':              stock,
        'snapshot_date':        today,
    })


def get_snapshot_history(vs_location_id, vs_product_id, days=35):
    """
    Fetch last N days of snapshots for one product+location.
    Returns list ordered by snapshot_date ASC.
    """
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    path = (
        f'/rest/v1/inventory_snapshots'
        f'?vetspire_location_id=eq.{vs_location_id}'
        f'&vetspire_product_id=eq.{vs_product_id}'
        f'&snapshot_date=gte.{cutoff}'
        f'&order=snapshot_date.asc'
        f'&select=snapshot_date,on_hand'
    )
    return supa_request('GET', path) or []


# ── Consumption calculation ───────────────────────────────────────────────────
def calc_avg_daily_usage(snapshots):
    """
    Calculate average daily consumption from snapshot history.
    Only counts days where on-hand DECREASED (usage days).
    Ignores days where on-hand went UP (restock days) or stayed flat.
    Returns avg units consumed per day, or None if insufficient data.
    """
    if len(snapshots) < MIN_DAYS_DATA:
        return None

    consumption_days = []
    for i in range(1, len(snapshots)):
        prev = float(snapshots[i-1]['on_hand'] or 0)
        curr = float(snapshots[i]['on_hand']   or 0)
        delta = prev - curr
        if delta > 0:  # stock decreased = usage day
            consumption_days.append(delta)

    if not consumption_days:
        return None

    return sum(consumption_days) / len(consumption_days)


def calc_min_max(avg_daily, is_peak):
    """
    Min = adjusted_daily × (lead_time + safety_days)
    Max = adjusted_daily × (lead_time + safety_days + order_cycle_days)
    All in Vetspire native units.
    """
    factor = PEAK_FACTOR if is_peak else OFFPEAK_FACTOR
    adjusted = avg_daily * factor
    min_val  = adjusted * (LEAD_TIME_DAYS + SAFETY_DAYS)
    max_val  = adjusted * (LEAD_TIME_DAYS + SAFETY_DAYS + ORDER_CYCLE_DAYS)
    return min_val, max_val


def is_peak_season():
    return datetime.date.today().month in PEAK_MONTHS


# ── Main sync ─────────────────────────────────────────────────────────────────
def run_sync(token, dry_run=False, location_filter=None):
    today      = datetime.date.today().isoformat()
    peak       = is_peak_season()
    season_str = 'PEAK' if peak else 'OFF-PEAK'

    print(f'\nMedSync → Vetspire Daily Sync  |  {today}  |  Season: {season_str}')
    print('=' * 60)
    if dry_run:
        print('DRY RUN — no writes to Vetspire\n')

    locations = {k: v for k, v in LOCATIONS.items()
                 if location_filter is None or k == location_filter}

    total_updated = 0
    total_skipped = 0
    total_errors  = 0

    for loc_name, vs_loc_id in locations.items():
        print(f'\n📍 {loc_name} (Vetspire ID: {vs_loc_id})')
        print('-' * 40)

        products = get_products_at_location(token, vs_loc_id)
        if not products:
            print('  No products returned — check token and location ID.')
            total_errors += 1
            continue

        print(f'  {len(products)} tracked products found.')

        for p in products:
            stock       = p['stock']
            vs_prod_id  = p['id']
            prod_name   = p['name']

            # 1. Store today's snapshot
            store_snapshot(vs_loc_id, loc_name, vs_prod_id, prod_name, stock)

            # 2. Get history and calculate usage
            history = get_snapshot_history(vs_loc_id, vs_prod_id)
            avg_daily = calc_avg_daily_usage(history)

            if avg_daily is None:
                days_so_far = len(history)
                print(f'  ⏳ {prod_name}: {days_so_far}/{MIN_DAYS_DATA} days data — skipping write')
                total_skipped += 1
                continue

            if avg_daily == 0:
                print(f'  ⚠  {prod_name}: zero consumption in history — skipping')
                total_skipped += 1
                continue

            # 3. Calculate new min/max
            new_min, new_max = calc_min_max(avg_daily, peak)

            print(f'  ✓ {prod_name}')
            print(f'    on-hand={stock:.1f}  avg_daily={avg_daily:.2f}  '
                  f'→ min={int(math.ceil(new_min))}  max={int(math.ceil(new_max))}')

            # 4. Write to Vetspire
            ok = write_threshold(token, vs_loc_id, vs_prod_id, new_min, new_max, dry_run)
            if ok:
                total_updated += 1
            else:
                print(f'    ❌ Write failed')
                total_errors += 1

    print(f'\n{"=" * 60}')
    print(f'Sync complete  |  updated={total_updated}  skipped={total_skipped}  errors={total_errors}')
    if total_errors:
        print('Check errors above — most likely the API token needs activation.')
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MedSync → Vetspire daily usage sync')
    parser.add_argument('--token',    required=True, help='Vetspire API token')
    parser.add_argument('--dry-run',  action='store_true', help='Preview changes without writing')
    parser.add_argument('--location', default=None,
                        help='Run for one location only (e.g. "Old Orchard")')
    args = parser.parse_args()

    run_sync(
        token=args.token,
        dry_run=args.dry_run,
        location_filter=args.location,
    )
