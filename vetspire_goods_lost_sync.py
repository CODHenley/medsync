#!/usr/bin/env python3
"""
MedSync — Vetspire Goods Lost Sync
-------------------------------------
Runs every 15 minutes via cron. Finds goods_lost records that have
not yet been pushed to Vetspire and creates an inventory adjustment
for each one, reducing on-hand by qty_lost.

Flow:
  1. Query Supabase: goods_lost WHERE vetspire_synced = FALSE
  2. For each record:
     a. Resolve location name → Vetspire location ID
     b. Resolve product name → Vetspire product ID (via inventory_snapshots)
     c. POST inventory adjustment mutation to Vetspire API
     d. Mark row as synced (or log error if mutation fails)

NOTE on Vetspire inventory adjustment mutation:
  The mutation name below (createInventoryAdjustment) follows Vetspire's
  confirmed GraphQL schema pattern. If this returns an "unknown field" error,
  contact Vetspire support to confirm the correct mutation name for
  reducing on-hand inventory. Auth header: Authorization: <token> (no Bearer).

Requires:
  pip install requests --break-system-packages

Usage:
  python3 vetspire_goods_lost_sync.py --token YOUR_VETSPIRE_TOKEN [--dry-run]

Cron (every 15 min):
  */15 * * * * /usr/bin/python3 /path/to/vetspire_goods_lost_sync.py \
    --token $(cat /path/to/vetspire_token.txt) >> /path/to/goods_lost_sync.log 2>&1
"""

import sys
import json
import datetime
import argparse
import urllib.request
import urllib.error
import urllib.parse

# ── Config ────────────────────────────────────────────────────────────────────
VETSPIRE_URL = 'https://api.vetspire.com/graphql'
SUPA_URL     = 'https://aemkdummdrmxtwrkggjw.supabase.co'
SUPA_KEY     = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s'

# Vetspire location IDs (must match vetspire_daily_sync.py)
LOCATIONS = {
    'Lincoln Park': '23083',
    'Old Orchard':  '27390',
    'West Loop':    '24356',
    'Wheaton':      '28253',
}

# ── Vetspire GraphQL ──────────────────────────────────────────────────────────
def vs_gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=payload,
        method='POST',
        headers={
            'Authorization': token,   # No Bearer prefix — confirmed by Vetspire support
            'Content-Type':  'application/json',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'errors': [{'message': f'HTTP {e.code}: {e.read().decode()[:200]}'}]}
    except Exception as e:
        return {'errors': [{'message': str(e)}]}


def create_inventory_adjustment(token, location_id, product_id, qty_lost, reason, dry_run):
    """
    Subtract qty_lost from Vetspire on-hand for a product at a location.

    Vetspire adjustment mutation — quantity is NEGATIVE to reduce on-hand.
    If this mutation name is wrong, Vetspire support can confirm the correct one.
    """
    if dry_run:
        print(f'    [DRY RUN] createInventoryAdjustment: loc={location_id} '
              f'product={product_id} qty={-qty_lost} reason="{reason}"')
        return True, None

    mutation = '''
    mutation createInventoryAdjustment($input: InventoryAdjustmentInput!) {
      createInventoryAdjustment(input: $input) {
        id
        quantity
        __typename
      }
    }'''

    result = vs_gql(token, mutation, {'input': {
        'locationId': str(location_id),
        'productId':  str(product_id),
        'quantity':   -abs(qty_lost),   # Always negative — reducing on-hand
        'reason':     reason,
    }})

    if 'errors' in result:
        err = result['errors'][0].get('message', str(result['errors']))
        return False, err

    return True, None


# ── Supabase helpers ──────────────────────────────────────────────────────────
def supa_get(path):
    req = urllib.request.Request(
        SUPA_URL + path,
        method='GET',
        headers={
            'apikey':        SUPA_KEY,
            'Authorization': 'Bearer ' + SUPA_KEY,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f'  Supabase GET error: {e}')
        return []


def supa_patch(path, body):
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        SUPA_URL + path,
        data=payload,
        method='PATCH',
        headers={
            'apikey':        SUPA_KEY,
            'Authorization': 'Bearer ' + SUPA_KEY,
            'Content-Type':  'application/json',
            'Prefer':        'return=minimal',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            return True
    except urllib.error.HTTPError as e:
        print(f'  Supabase PATCH error: HTTP {e.code}: {e.read().decode()[:200]}')
        return False
    except Exception as e:
        print(f'  Supabase PATCH error: {e}')
        return False


def get_unsynced_losses():
    """
    Fetch goods_lost rows not yet pushed to Vetspire.
    Uses product_name (stored at submission) and locations join for location name.
    """
    rows = supa_get(
        '/rest/v1/goods_lost'
        '?select=id,location_id,qty_lost,category,notes,created_at,'
        'product_name,locations(name)'
        '&vetspire_synced=eq.false'
        '&order=created_at.asc'
        '&limit=100'
    )
    return rows if isinstance(rows, list) else []


def get_vetspire_product_id(location_name, product_name):
    """
    Look up Vetspire product ID from inventory_snapshots using
    location name + product name (populated by vetspire_daily_sync.py).
    Returns None if no snapshot found yet.
    """
    vs_loc_id = LOCATIONS.get(location_name)
    if not vs_loc_id:
        return None

    rows = supa_get(
        f'/rest/v1/inventory_snapshots'
        f'?select=vetspire_product_id'
        f'&vetspire_location_id=eq.{vs_loc_id}'
        f'&product_name=eq.{urllib.parse.quote(product_name)}'
        f'&order=snapshot_date.desc'
        f'&limit=1'
    )
    if rows and len(rows) > 0:
        return rows[0].get('vetspire_product_id')
    return None


def mark_synced(loss_id, success, error_msg=None):
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    body = {
        'vetspire_synced':    success,
        'vetspire_synced_at': now if success else None,
        'vetspire_sync_error': error_msg,
    }
    supa_patch(f'/rest/v1/goods_lost?id=eq.{loss_id}', body)


# ── Main ──────────────────────────────────────────────────────────────────────
def run_sync(token, dry_run=False):

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n[{now}] MedSync — Vetspire Goods Lost Sync')
    print(f'  Mode: {"DRY RUN" if dry_run else "LIVE"}')

    losses = get_unsynced_losses()
    print(f'  Unsynced losses: {len(losses)}')

    if not losses:
        print('  Nothing to sync.')
        return

    synced = 0
    failed = 0

    for loss in losses:
        loss_id      = loss.get('id')
        qty_lost     = float(loss.get('qty_lost') or 0)
        category     = loss.get('category', 'Unknown')
        notes        = loss.get('notes') or ''
        location_obj  = loss.get('locations') or {}
        location_name = location_obj.get('name') if isinstance(location_obj, dict) else None
        product_name  = loss.get('product_name')

        print(f'\n  Processing: {product_name} @ {location_name} · qty={qty_lost} · {category}')

        # Validate
        if not location_name:
            print(f'    ✗ No location name — skipping')
            mark_synced(loss_id, False, 'No location name resolved')
            failed += 1
            continue

        if not product_name:
            print(f'    ✗ No product name — skipping')
            mark_synced(loss_id, False, 'No product name resolved')
            failed += 1
            continue

        if qty_lost <= 0:
            print(f'    ✗ qty_lost={qty_lost} — skipping')
            mark_synced(loss_id, True, None)  # Mark done — nothing to subtract
            synced += 1
            continue

        vs_loc_id = LOCATIONS.get(location_name)
        if not vs_loc_id:
            print(f'    ✗ Location "{location_name}" not in LOCATIONS dict')
            mark_synced(loss_id, False, f'Unknown location: {location_name}')
            failed += 1
            continue

        vs_product_id = get_vetspire_product_id(location_name, product_name)
        if not vs_product_id:
            print(f'    ✗ No Vetspire product ID found for "{product_name}" at {location_name}')
            print(f'      (inventory_snapshots may not have this product yet — will retry next run)')
            # Don't mark as error — leave unsynced so it retries when snapshots populate
            continue

        # Build reason string for Vetspire
        reason = f'MedSync goods lost — {category}'
        if notes:
            reason += f': {notes[:80]}'

        ok, err = create_inventory_adjustment(
            token, vs_loc_id, vs_product_id, qty_lost, reason, dry_run
        )

        if ok:
            print(f'    ✓ Vetspire adjustment written: -{qty_lost} units')
            if not dry_run:
                mark_synced(loss_id, True)
            synced += 1
        else:
            print(f'    ✗ Vetspire mutation failed: {err}')
            mark_synced(loss_id, False, str(err)[:500])
            failed += 1

    print(f'\n  Done — synced: {synced}  failed: {failed}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MedSync Goods Lost → Vetspire Sync')
    parser.add_argument('--token',   required=True, help='Vetspire API token')
    parser.add_argument('--dry-run', action='store_true', help='Print without writing to Vetspire')
    args = parser.parse_args()

    run_sync(args.token, dry_run=args.dry_run)
