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

    # 4. Argument signatures for the specific root query fields the actual clinical sync
    # will call — field names alone aren't enough to write working queries, and guessing
    # args wrong here means a wasted CI run same as the earlier auth-header mistake.
    sync_targets = [
        'encountersUpdatedSince', 'encounters', 'listEncounters',
        'patients', 'patient', 'clients', 'client',
        'providers', 'provider', 'appointments', 'countNewClients',
        'clientReferralSources',
    ]
    print('=== Args for the query fields the clinical sync will call ===')
    r = gql(args.token, '{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    by_name = {f['name']: f for f in fields}
    for name in sync_targets:
        f = by_name.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        arg_strs = []
        for a in f.get('args', []):
            arg_strs.append(f"{a['name']}: {type_name(a['type'])}")
        print(f"  {name}({', '.join(arg_strs) if arg_strs else '(no args)'})")
    print()

    # 5. salesReport/salesTypedReport args + their breakdown enum's real values, then a
    # live test call built ONLY from what was just introspected (no hardcoded enum
    # value guesses) — today's revenue sync calls salesReport with no breakdown arg at
    # all and gets one row per location/date (just `total`); Financial KPIs (ATC,
    # Revenue by Source, Revenue per Vet) need the row-level detail breakdown unlocks.
    print('=== salesReport / salesTypedReport args ===')
    sales_arg_types = {}  # field_name -> {arg_name: type_name}
    for name in ['salesReport', 'salesTypedReport']:
        f = by_name.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        sales_arg_types[name] = {}
        for a in f.get('args', []):
            tname = type_name(a['type'])
            sales_arg_types[name][a['name']] = tname
            print(f"  {name}.{a['name']}: {tname}")
    print()

    print('=== Breakdown enum values ===')
    breakdown_enum_values = {}  # arg_type_name -> [values]
    for field_name, arg_types in sales_arg_types.items():
        for arg_name, tname in arg_types.items():
            if 'breakdown' not in arg_name.lower() or tname in breakdown_enum_values:
                continue
            r = gql(args.token, f'{{ __type(name: "{tname}") {{ name enumValues {{ name }} }} }}')
            data = (r.get('data') or {}).get('__type')
            if not data:
                print(f'  (type "{tname}" not found)')
                continue
            values = [v['name'] for v in (data.get('enumValues') or [])]
            breakdown_enum_values[tname] = values
            print(f"  {tname}: {values}")
    print()

    print('=== Live salesReport test w/ breakdown (built from the above, not guessed) ===')
    sr_args = sales_arg_types.get('salesReport', {})
    breakdown_arg_name = next((a for a in sr_args if 'breakdown' in a.lower()), None)
    if breakdown_arg_name and breakdown_enum_values:
        enum_type = sr_args[breakdown_arg_name]
        values = breakdown_enum_values.get(enum_type, [])
        provider_val = next((v for v in values if 'PROVIDER' in v), None)
        category_val = next((v for v in values if 'CATEGORY' in v), None)
        test_breakdown = [v for v in (provider_val, category_val) if v] or values[:2]
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        test_query = f'''
        query($lids:[ID!], $s:Date, $e:Date, $bd:[{enum_type}!]){{
            salesReport(locationIds:$lids, startDate:$s, endDate:$e, {breakdown_arg_name}:$bd)
        }}
        '''
        r = gql(args.token, test_query, {
            'lids': ['28253'], 's': yesterday, 'e': yesterday, 'bd': test_breakdown,
        })
        print(f'  breakdown used: {test_breakdown}')
        print(f'  result: {json.dumps(r)[:3000]}')
    else:
        print('  (no breakdown arg found on salesReport — skipping live test)')
    print()

    # 6. The prior live test returned "date":"2026-08" (month-level) for a single-day
    # query — checking the `segment` arg's real enum values before assuming daily
    # financial granularity is even possible, rather than guessing DAY/DAILY as a string.
    print('=== ReportSegment enum values + live test with segment set ===')
    segment_arg_name = next((a for a in sr_args if 'segment' in a.lower()), None)
    if segment_arg_name:
        seg_type = sr_args[segment_arg_name]
        r = gql(args.token, f'{{ __type(name: "{seg_type}") {{ name enumValues {{ name }} }} }}')
        data = (r.get('data') or {}).get('__type')
        seg_values = [v['name'] for v in (data or {}).get('enumValues', [])] if data else []
        print(f"  {seg_type}: {seg_values}")
        day_val = next((v for v in seg_values if 'DAY' in v), None)
        if day_val and breakdown_arg_name and breakdown_enum_values:
            enum_type = sr_args[breakdown_arg_name]
            values = breakdown_enum_values.get(enum_type, [])
            provider_val = next((v for v in values if 'PROVIDER' in v), None)
            test_breakdown = [v for v in (provider_val,) if v] or values[:1]
            test_query = f'''
            query($lids:[ID!], $s:Date, $e:Date, $bd:[{enum_type}!], $seg:{seg_type}){{
                salesReport(locationIds:$lids, startDate:$s, endDate:$e, {breakdown_arg_name}:$bd, {segment_arg_name}:$seg)
            }}
            '''
            r2 = gql(args.token, test_query, {
                'lids': ['28253'], 's': yesterday, 'e': yesterday,
                'bd': test_breakdown, 'seg': day_val,
            })
            print(f'  segment used: {day_val}, breakdown used: {test_breakdown}')
            print(f'  result: {json.dumps(r2)[:2000]}')
        else:
            print('  (no DAY-like segment value found, or no breakdown to pair it with)')
    else:
        print('  (no segment arg found on salesReport)')
    print()

    # 7. referral_type classification (true rDVM vs. competitor urgent care/ER):
    # Rdvm.tags: EntityTag was confirmed in a prior run, but EntityTag itself was
    # never dumped (it doesn't match any KEYWORDS substring), and neither did the
    # root `rdvms` query field's args. Both needed before designing a classification
    # sync — plus a live sample of what's actually tagged today, so we design against
    # real data instead of assuming Megan has (or hasn't) already tagged anything.
    print('=== EntityTag fields ===')
    dump_type_fields(args.token, 'EntityTag')

    print('=== rdvms / rdvmsCount / searchRdvms args ===')
    r = gql(args.token, '{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    by_name2 = {f['name']: f for f in fields}
    for name in ['rdvms', 'rdvmsCount', 'searchRdvms']:
        f = by_name2.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        arg_strs = [f"{a['name']}: {type_name(a['type'])}" for a in f.get('args', [])]
        print(f"  {name}({', '.join(arg_strs) if arg_strs else '(no args)'})")
    print()

    print('=== Live sample: first 50 rdvms with their tags ===')
    r = gql(args.token, '{ rdvms(limit: 50) { id name isActive tags { id name } } }')
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rdvms = (r.get('data') or {}).get('rdvms') or []
        print(f'  fetched {len(rdvms)} rdvms')
        tag_names = set()
        for rd in rdvms:
            tags = rd.get('tags') or []
            if tags:
                names = [t.get('name') for t in tags]
                tag_names.update(names)
                print(f'  - {rd.get("name")!r}: tags={names}')
        print(f'  distinct tag names seen: {sorted(tag_names)}')
    print()


if __name__ == '__main__':
    main()
