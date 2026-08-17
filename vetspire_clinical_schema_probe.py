#!/usr/bin/env python3
"""
vetspire_clinical_schema_probe.py
Discovers the real Vetspire GraphQL field/type names needed for ScoutSync's
Clinical Operations and Financial sections — encounter-start ("arrived") events,
referral/rDVM relationships, records-release logging, provider/staff roster,
and invoice line-item detail.

This only runs where the environment has network access to api.vetspire.com
(it is blocked by policy in this Claude Code Remote session — run it locally
or wire it into a GitHub Actions step, same as wheaton_lot_sync.py).

Usage:
  python3 vetspire_clinical_schema_probe.py --token-file ~/.vetspire_token
  python3 vetspire_clinical_schema_probe.py --token "Bearer eyJ..."
"""
import sys, json, argparse, urllib.request, urllib.error

VETSPIRE_URL = 'https://api.vetspire.com/graphql'

KEYWORDS = [
    'encounter', 'appointment', 'arrive', 'checkin', 'check_in',
    'referral', 'rdvm', 'referring',
    'record', 'release', 'transfer', 'communication', 'letter',
    'client', 'patient', 'provider', 'staff', 'employee',
    'invoice', 'sale', 'transaction', 'charge', 'payment',
]


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    # The permanent API key (VETSPIRE_API_TOKEN) goes in raw, no "Bearer " prefix —
    # same auth pattern as wheaton_lot_sync.py / nightly_revenue_sync.py.
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def type_name(t):
    return t.get('name') or (t.get('ofType') or {}).get('name') or t.get('kind')


def dump_type_fields(token, type_name_str):
    r = gql(token, f'{{ __type(name: "{type_name_str}") {{ name fields {{ name type {{ name kind ofType {{ name kind ofType {{ name }} }} }} }} }} }}')
    data = (r.get('data') or {}).get('__type')
    if not data:
        print(f'  (type "{type_name_str}" not found — errors: {r.get("errors")})')
        return
    print(f'=== {type_name_str} fields ===')
    for f in sorted(data['fields'], key=lambda x: x['name']):
        tname = type_name(f['type'])
        flag = ' ***' if any(k in f['name'].lower() for k in KEYWORDS) else ''
        print(f'  {f["name"]}: {tname}{flag}')
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--token-file')
    args = parser.parse_args()

    if args.token_file:
        import os
        with open(os.path.expanduser(args.token_file)) as f:
            args.token = f.read().strip()
    if not args.token:
        print('ERROR: provide --token or --token-file')
        raise SystemExit(1)
    args.token = args.token.strip().removeprefix('Bearer ').strip()

    print('=== Connection test ===')
    try:
        r = gql(args.token, '{ __typename }')
        print(f'OK: {r}\n')
    except urllib.error.HTTPError as e:
        print(f'FAILED: HTTP {e.code} — {e.read()[:300]}')
        raise SystemExit(1)

    # 1. All root Query fields matching our keywords — tells us what's queryable at all
    print('=== Query root fields matching keywords ===')
    r = gql(args.token, '{ __schema { queryType { fields { name description } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    for f in fields:
        name = f.get('name', '')
        if any(k in name.lower() for k in KEYWORDS):
            print(f'  ★ {name}: {f.get("description", "")}')
    print(f'  (Total query fields: {len(fields)})\n')

    # 2. All schema type names matching our keywords — tells us the real object type names
    #    (e.g. it might be "Appointment" not "Encounter", "ReferralSource" not "Referral")
    print('=== Schema type names matching keywords ===')
    r = gql(args.token, '{ __schema { types { name kind } } }')
    types = (r.get('data') or {}).get('__schema', {}).get('types', [])
    candidates = sorted(
        t['name'] for t in types
        if t['kind'] == 'OBJECT' and any(k in t['name'].lower() for k in KEYWORDS)
    )
    for name in candidates:
        print(f'  ★ {name}')
    print()

    # 3. Dump fields for the most likely candidates outright (safe no-ops if they don't exist)
    likely_types = [
        'Patient', 'Client', 'Encounter', 'Appointment', 'Visit',
        'Referral', 'ReferralSource', 'Provider', 'Staff', 'Employee',
        'Invoice', 'InvoiceLineItem', 'Transaction',
    ]
    # Merge in whatever the keyword scan actually found, de-duped, so we don't miss
    # a type named something we didn't guess (e.g. "ClientReferral").
    all_targets = sorted(set(likely_types) | set(candidates))
    for t in all_targets:
        dump_type_fields(args.token, t)


if __name__ == '__main__':
    main()
