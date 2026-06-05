"""
MedSync → Vetspire Seasonal Min/Max Sync
-----------------------------------------
Reads demand forecast spreadsheet, calculates peak vs off-peak reorder points
per product per location, and pushes to Vetspire via upsertLowStockThreshold.

Usage:
    python3 vetspire_sync_minmax.py --token YOUR_VETSPIRE_API_KEY [--dry-run]

Peak season: May – October (months 5–10)
Off-peak:    November – April
"""

import sys
import os
import json
import datetime
import argparse
import pandas as pd
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
VETSPIRE_URL  = 'https://api.vetspire.com/graphql'
SPREADSHEET   = '/Users/meganhenley/Downloads/medsync_deploy/Demand_Forecasting_Spreadsheet_2026_v4 (2).xlsx'

# Vetspire product name → Supabase/MedSync name mapping
# Key = keyword to match in Usage Trends sheet, Value = Vetspire product name fragment
PRODUCT_MAP = {
    'Acepromazine':        'Acepromazine 10mg/ml',
    'Buprenorphine  Inj':  'Buprenorphine 0.3mg/ml',
    'Carprofen 50':        'Carprofen 50mg tabs',
    'Dexmedetomidine Inj': 'Dexmedetomidine 0.5mg/ml',
    'Gabapentin 100 mg c': 'Gabapentin 100mg caps',
    'Hydromorphone Inj':   'Hydromorphone 2mg/ml',
    'Ketamine HCl Inj':    'Ketamine HCl 10mg/ml',
    'Maropitant Inj':      'Maropitant Citrate 10mg/ml',
    'Meloxicam Susp':      'Meloxicam 5mg/ml inj',
    'Ondansetron Inj':     'Ondansetron 2mg/ml inj',
    'Tramadol':            'Tramadol 50mg tabs',
    'Vanguard DAPP Vaccine':'Vanguard DAPP vaccine',
}

# Vetspire location IDs (from More → Admin → Locations)
LOCATION_IDS = {
    'Lincoln Park': '23083',
    'Old Orchard':  '27390',
    'West Loop':    '24356',
    'Wheaton':      '28253',
}

# ── GraphQL helpers ──────────────────────────────────────────────────────────
def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    # Vetspire uses Authorization: Bearer (confirmed via GraphQL Network Inspector)
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def test_connectivity(token):
    # Minimal query — just confirms auth is working
    q = '''query { __typename }'''
    return gql(token, q)

def list_products(token, location_id, limit=20, offset=0):
    """
    Uses the real getProductCounts query structure confirmed via GraphQL inspector.
    Vetspire paginates at 20/page — caller should loop with offset to get all.
    Fields confirmed: id, name. minimumThreshold/stockCount to be verified
    once upsertLowStockThreshold mutation response is captured.
    """
    q = '''query getProductCounts(
      $locationId: ID!
      $limit: Int
      $offset: Int
      $sortBy: SortProductOptions
      $sortField: String
      $sortDirection: String
    ) {
      products(
        onlyTrackInventory: true
        onlyEnabledAt: $locationId
        limit: $limit
        offset: $offset
      ) {
        id
        name
        minimumThreshold
        maximumQuantity
      }
    }'''
    return gql(token, q, {
        'locationId':    str(location_id),
        'limit':         limit,
        'offset':        offset,
        'sortBy':        'ALPHABETICAL',
        'sortField':     'name',
        'sortDirection': 'asc',
    })

def list_all_products(token, location_id):
    """Paginates through all products at a location, 20 at a time."""
    all_products = []
    offset = 0
    while True:
        result = list_products(token, location_id, limit=20, offset=offset)
        page = result.get('data', {}).get('products', [])
        if not page:
            break
        all_products.extend(page)
        if len(page) < 20:
            break
        offset += 20
    return all_products

def upsert_threshold(token, location_id, product_id, threshold, max_qty, dry_run=False):
    """
    Confirmed via GraphQL inspector on scoutcare.vetspire.com:
      - threshold      = Minimum Threshold (the reorder point)
      - reorderQuantity = Maximum Quantity (the restocking target)
      - response does NOT include productId — removed to avoid schema error
    Variables confirmed: locationId "23083", productId "646466", threshold 5, reorderQuantity 10
    """
    if dry_run:
        print(f'  [DRY RUN] locationId={location_id} productId={product_id} '
              f'min={threshold} max={max_qty}')
        return True
    q = '''
    mutation upsertLowStockThreshold($input: LowStockThresholdInput!) {
      upsertLowStockThreshold(input: $input) {
        id
        locationId
        threshold
        reorderQuantity
        __typename
      }
    }'''
    result = gql(token, q, {'input': {
        'locationId':      str(location_id),
        'productId':       str(product_id),
        'threshold':       int(threshold),
        'reorderQuantity': int(max_qty),
    }})
    return 'errors' not in result

# ── Demand forecast ──────────────────────────────────────────────────────────
def is_peak_season():
    """May (5) through October (10) inclusive."""
    return datetime.date.today().month in range(5, 11)

def load_location_rop(location_name, keyword):
    """
    Load monthly usage for a product at a location from the spreadsheet.
    Returns (peak_rop, off_rop) as package quantities (ceiling'd).
    """
    sheet = f'_UT_2025_{location_name}'
    try:
        df = pd.read_excel(SPREADSHEET, sheet_name=sheet, header=None)
    except Exception:
        return None, None

    mask = df.apply(lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)
    matches = df[mask]
    if matches.empty:
        return None, None

    row = matches.iloc[0]
    monthly = []
    for i in range(2, 14):
        try:
            monthly.append(float(row[i]))
        except Exception:
            monthly.append(0.0)

    peak    = sum(monthly[4:10])   # May–Oct (11 two-week periods)
    offpeak = sum(monthly) - peak  # Nov–Apr (15 two-week periods)

    peak_rop   = max(1, round(peak / 11))    if peak    > 0 else 1
    off_rop    = max(1, round(offpeak / 15)) if offpeak > 0 else 1
    peak_max   = peak_rop   * 2
    off_max    = off_rop    * 2

    return (peak_rop, peak_max) if is_peak_season() else (off_rop, off_max)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token',          required=False, help='Vetspire API token')
    parser.add_argument('--token-file',     required=False, help='Path to file containing Vetspire API token')
    parser.add_argument('--dry-run',        action='store_true', help='Print changes without writing')
    parser.add_argument('--list-locations', action='store_true', help='Print location IDs and exit')
    parser.add_argument('--list-products',  action='store_true', help='Print product IDs and exit')
    args = parser.parse_args()

    if args.token_file:
        with open(args.token_file.replace('~', os.path.expanduser('~')), 'r') as f:
            args.token = f.read().strip()
    if not args.token:
        print('ERROR: provide --token or --token-file')
        sys.exit(1)

    season = 'PEAK (May–Oct)' if is_peak_season() else 'OFF-PEAK (Nov–Apr)'
    print(f'Season: {season}')
    print(f'Dry run: {args.dry_run}\n')

    if args.list_locations:
        result = list_locations(args.token)
        print(json.dumps(result.get('data', {}).get('locations', []), indent=2))
        return

    if args.list_products:
        result = list_products(args.token)
        nodes = result.get('data', {}).get('products', {}).get('nodes', [])
        for n in nodes:
            print(f"{n['id']:>10}  {n['name']}")
        return

    # Verify location IDs are filled in
    missing_locs = [k for k, v in LOCATION_IDS.items() if v is None]
    if missing_locs:
        print('ERROR: Fill in LOCATION_IDS in this script first.')
        print('Run with --list-locations to get the IDs.')
        print('Missing:', missing_locs)
        sys.exit(1)

    # Get Vetspire product ID map
    result = list_products(args.token)
    nodes = result.get('data', {}).get('products', {}).get('nodes', [])
    vs_products = {n['name']: n['id'] for n in nodes}

    ok = 0
    fail = 0

    for keyword, vs_name_fragment in PRODUCT_MAP.items():
        # Find Vetspire product ID
        prod_id = next((v for k, v in vs_products.items()
                        if vs_name_fragment.lower() in k.lower()), None)
        if not prod_id:
            print(f'SKIP (no Vetspire product): {vs_name_fragment}')
            continue

        print(f'\n{vs_name_fragment} (id={prod_id})')

        for loc_name, loc_id in LOCATION_IDS.items():
            rop = load_location_rop(loc_name, keyword)
            if rop == (None, None):
                print(f'  {loc_name}: no usage data — skipping')
                continue
            threshold, reorder_qty = rop
            success = upsert_threshold(args.token, loc_id, prod_id,
                                       threshold, reorder_qty, args.dry_run)
            status = 'OK' if success else 'FAILED'
            print(f'  {loc_name}: min={threshold} max={reorder_qty} → {status}')
            if success:
                ok += 1
            else:
                fail += 1

    print(f'\nDone. {ok} updated, {fail} failed.')

if __name__ == '__main__':
    main()
