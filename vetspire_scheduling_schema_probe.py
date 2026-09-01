#!/usr/bin/env python3
"""
One-off: search Vetspire's real GraphQL schema for anything that would let
us tell "staff scheduled but no revenue/encounters that day" (a real open
day) apart from "actually closed" -- a staff shift/schedule/roster type, a
practice hours/closure calendar, or an Appointment type queryable
independent of Encounter (a booked/no-show appointment would mean the
practice was open and taking appointments even with zero billed revenue).

Lists all type names matching scheduling-ish keywords, all root Query
fields matching the same, and dumps fields for any match.
"""
import argparse, json, os, urllib.request, urllib.error

VETSPIRE_URL = 'https://api.vetspire.com/graphql'

KEYWORDS = [
    'schedule', 'shift', 'roster', 'hours', 'holiday', 'closure', 'closed',
    'availability', 'timeoff', 'time_off', 'staffing', 'appointment',
    'calendar', 'workday', 'work_day', 'openhours', 'businesshours',
]


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def type_name(t):
    return t.get('name') or (t.get('ofType') or {}).get('name') or t.get('kind')


def dump_type_fields(token, type_name_str):
    # One bad type (introspection depth limit, a union/interface with no
    # plain `fields`, a transient network error) shouldn't kill the whole
    # probe -- every call site wraps this and keeps going.
    try:
        r = gql(token, f'{{ __type(name: "{type_name_str}") {{ name kind fields {{ name type {{ name kind ofType {{ name kind ofType {{ name }} }} }} args {{ name type {{ name kind ofType {{ name }} }} }} }} }} }}')
    except urllib.error.HTTPError as e:
        print(f'  (type "{type_name_str}" — HTTP {e.code}: {e.read()[:400]})')
        return
    except Exception as e:
        print(f'  (type "{type_name_str}" — request failed: {e!r})')
        return
    data = (r.get('data') or {}).get('__type')
    if not data or not data.get('fields'):
        print(f'  (type "{type_name_str}" not found or has no fields — errors: {r.get("errors")})')
        return
    print(f'=== {type_name_str} fields ===')
    for f in sorted(data['fields'], key=lambda x: x['name']):
        tname = type_name(f['type'])
        args = ', '.join(f"{a['name']}: {type_name(a['type'])}" for a in (f.get('args') or []))
        print(f'  {f["name"]}({args}): {tname}')
    print()


def dump_enum_values(token, type_name_str):
    try:
        r = gql(token, f'{{ __type(name: "{type_name_str}") {{ name enumValues {{ name }} }} }}')
        data = (r.get('data') or {}).get('__type')
        values = [v['name'] for v in (data or {}).get('enumValues') or []]
        print(f'=== {type_name_str} enum values === {values}\n')
    except Exception as e:
        print(f'  (enum "{type_name_str}" — request failed: {e!r})')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--token-file')
    args = parser.parse_args()
    if args.token_file:
        with open(os.path.expanduser(args.token_file)) as f:
            args.token = f.read().strip()
    if not args.token:
        raise SystemExit('ERROR: provide --token or --token-file')
    args.token = args.token.strip().removeprefix('Bearer ').strip()

    print('=== All type names matching scheduling keywords ===')
    r = gql(args.token, '{ __schema { types { name kind } } }')
    all_types = (r.get('data') or {}).get('__schema', {}).get('types', [])
    matches = [t for t in all_types if any(k in t['name'].lower() for k in KEYWORDS)]
    for t in sorted(matches, key=lambda x: x['name']):
        print(f"  {t['name']} ({t['kind']})")
    print()

    print('=== Root Query fields matching scheduling keywords ===')
    r = gql(args.token, '''
    {
      __schema {
        queryType {
          fields {
            name
            type { name kind ofType { name kind ofType { name } } }
            args { name type { name kind ofType { name } } }
          }
        }
      }
    }
    ''')
    qfields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    qmatches = [f for f in qfields if any(k in f['name'].lower() for k in KEYWORDS)]
    for f in sorted(qmatches, key=lambda x: x['name']):
        tname = type_name(f['type'])
        # NOTE: intentionally not named `args` -- that would shadow the
        # argparse Namespace of the same name for the rest of main(), since
        # Python has no block scoping (this exact bug crashed the first run).
        argstr = ', '.join(f"{a['name']}: {type_name(a['type'])}" for a in (f.get('args') or []))
        print(f"  {f['name']}({argstr}): {tname}")
    print()

    print('=== Also checking known types for scheduling-ish fields: Provider, Appointment, Location ===')
    for t in ['Provider', 'Appointment', 'Location']:
        dump_type_fields(args.token, t)

    print('=== AppointmentStatus enum values ===')
    dump_enum_values(args.token, 'AppointmentStatus')

    print('=== Dumping fields for each matched scheduling-ish type ===')
    for t in matches:
        if t['kind'] == 'OBJECT':
            dump_type_fields(args.token, t['name'])
        elif t['kind'] == 'ENUM':
            dump_enum_values(args.token, t['name'])


if __name__ == '__main__':
    main()
