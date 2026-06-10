"""
pull_vetspire_minmax.py
-----------------------
Reads inventory thresholds from Vetspire for every inventory-tracked product
at each location, then writes qty_min / qty_max to the MedSync Supabase
products table.

Uses inventoryLevels[].lowStockThreshold as qty_min (correct Vetspire field).
Uses maxOrderLimit as qty_max; falls back to 3× min if not set.

Usage:
    python3 pull_vetspire_minmax.py --token-file ~/token.txt [--dry-run]
    python3 pull_vetspire_minmax.py --token YOUR_TOKEN [--dry-run]
"""

import sys
import json
import argparse
import urllib.request
import urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────
VETSPIRE_URL = 'https://api.vetspire.com/graphql'
SUPA_URL     = 'https://aemkdummdrmxtwrkggjw.supabase.co'
SUPA_KEY     = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s'

LOCATION_IDS = {
    'Lincoln Park': '23083',
    'Old Orchard':  '27390',
    'West Loop':    '24356',
    'Wheaton':      '28253',
}

# ── GraphQL helpers ───────────────────────────────────────────────────────────
def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': token,
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())

def fetch_products_page(token, location_id, limit=50, offset=0):
    q = '''query getProducts($locationId: ID!, $limit: Int, $offset: Int) {
      products(
        onlyTrackInventory: true
        onlyEnabledAt: $locationId
        limit: $limit
        offset: $offset
      ) {
        id
        name
        trackInventory
        maxOrderLimit
        inventoryLevels {
          locationId
          locationName
          stock
          lowStockThreshold
        }
      }
    }'''
    return gql(token, q, {
        'locationId': str(location_id),
        'limit': limit,
        'offset': offset,
    })

def fetch_all_products(token, location_id):
    all_products = []
    offset = 0
    while True:
        result = fetch_products_page(token, location_id, limit=50, offset=offset)
        if 'errors' in result:
            print(f'  GraphQL error: {result["errors"]}')
            break
        page = (result.get('data') or {}).get('products') or []
        if not page:
            break
        all_products.extend(page)
        if len(page) < 50:
            break
        offset += 50
    return all_products

# ── Supabase helpers ──────────────────────────────────────────────────────────
_supa_products = None  # cache

def load_supa_products():
    global _supa_products
    if _supa_products is not None:
        return _supa_products
    url = f'{SUPA_URL}/rest/v1/products?select=id,name&limit=2000'
    req = urllib.request.Request(url, headers={
        'apikey': SUPA_KEY, 'Authorization': f'Bearer {SUPA_KEY}'
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        _supa_products = json.loads(r.read())
    print(f'  [Supabase] Loaded {len(_supa_products)} products for matching')
    return _supa_products

def tokenize(name):
    """Lowercase alphanumeric tokens, length >= 2."""
    import re
    return set(t for t in re.split(r'[^a-z0-9]+', name.lower()) if len(t) >= 2)

def best_supa_match(vetspire_name, min_score=0.4):
    """Find best Supabase product by token overlap. Returns (product, score) or (None, 0)."""
    products = load_supa_products()
    vtoks = tokenize(vetspire_name)
    if not vtoks:
        return None, 0
    best, best_score = None, 0
    for p in products:
        stoks = tokenize(p['name'])
        if not stoks:
            continue
        overlap = len(vtoks & stoks)
        score = overlap / len(vtoks | stoks)  # Jaccard
        if score > best_score:
            best_score = score
            best = p
    if best_score >= min_score:
        return best, best_score
    return None, best_score

def supabase_patch(product_id, qty_min, qty_max):
    patch_url = f'{SUPA_URL}/rest/v1/products?id=eq.{product_id}'
    body = json.dumps({'qty_min': qty_min, 'qty_max': qty_max}).encode()
    req = urllib.request.Request(patch_url, data=body, method='PATCH', headers={
        'apikey': SUPA_KEY,
        'Authorization': f'Bearer {SUPA_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    })
    with urllib.request.urlopen(req, timeout=10):
        pass

def supabase_update_minmax(name, qty_min, qty_max, dry_run=False):
    """Update qty_min and qty_max on the products table using fuzzy name matching."""
    if dry_run:
        # In dry-run just show the Vetspire data — no Supabase needed
        print(f'    [DRY RUN] {name}: min={qty_min} max={qty_max}')
        return True

    try:
        match, score = best_supa_match(name)
    except Exception as e:
        print(f'    [ERROR] Supabase lookup failed for "{name}": {e}')
        return False

    if match is None:
        print(f'    [SKIP] No match (best score too low) for: {name}')
        return False

    try:
        supabase_patch(match['id'], qty_min, qty_max)
        print(f'    [OK] "{match["name"]}" (score={score:.2f}) → min={qty_min} max={qty_max}')
        return True
    except Exception as e:
        print(f'    [ERROR] Patch failed for "{match["name"]}": {e}')
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token',      required=False, help='Vetspire API token')
    parser.add_argument('--token-file', required=False, help='Path to file containing token')
    parser.add_argument('--dry-run',    action='store_true')
    args = parser.parse_args()

    if args.token_file:
        import os
        with open(os.path.expanduser(args.token_file)) as f:
            args.token = f.read().strip()
    if not args.token:
        print('ERROR: provide --token or --token-file')
        sys.exit(1)

    # Collect thresholds across all locations
    # Key: product name (lowercase), Value: {name, min, max}
    consolidated = {}

    for loc_name, loc_id in LOCATION_IDS.items():
        print(f'\nFetching {loc_name} (id={loc_id})...')
        products = fetch_all_products(args.token, loc_id)
        print(f'  {len(products)} inventory-tracked products')

        for p in products:
            # Get the lowStockThreshold for this specific location from inventoryLevels
            levels = p.get('inventoryLevels') or []
            loc_level = next((l for l in levels if str(l.get('locationId')) == str(loc_id)), None)
            if loc_level is None and levels:
                loc_level = levels[0]  # fallback to first level

            mn = (loc_level or {}).get('lowStockThreshold')
            mx = p.get('maxOrderLimit')

            # Skip products with no threshold set
            if mn is None:
                continue

            # If no max, default to 3× min
            if not mx:
                mx = mn * 3

            key = p['name'].lower()
            existing = consolidated.get(key)
            if existing is None:
                consolidated[key] = {'name': p['name'], 'min': mn, 'max': mx}
            else:
                # Take the highest min across locations (conservative)
                if mn > existing['min']:
                    consolidated[key]['min'] = mn
                if mx > existing['max']:
                    consolidated[key]['max'] = mx

    print(f'\n─── Found {len(consolidated)} products with thresholds set in Vetspire ───\n')

    if not consolidated:
        print('No products with thresholds found.')
        print('This means either:')
        print('  1. No products have lowStockThreshold set in Vetspire')
        print('  2. The onlyTrackInventory filter returned 0 results')
        print('\nTry checking a single location without filters:')
        print('  python3 vetspire_list_products.py --token-file ~/token.txt')
        sys.exit(1)

    ok = 0
    skip = 0
    for key, data in sorted(consolidated.items()):
        print(f'{data["name"]}: min={data["min"]} max={data["max"]}')
        if not args.dry_run:
            success = supabase_update_minmax(data['name'], data['min'], data['max'])
            if success:
                ok += 1
            else:
                skip += 1

    if args.dry_run:
        print(f'\n[DRY RUN] Would update {len(consolidated)} products in Supabase.')
    else:
        print(f'\nDone. {ok} updated, {skip} skipped (no Supabase match).')
        print('\nReload the weekly order screen — items below min will auto-flag with correct units.')

if __name__ == '__main__':
    main()
