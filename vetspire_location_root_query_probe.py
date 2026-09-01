#!/usr/bin/env python3
"""One-off: find the root Query field(s) for fetching a Location by id, so
providerSchedules can be queried nested under it (that field only exists on
the Location type, not as its own root query)."""
import argparse, json, os, urllib.request

VETSPIRE_URL = 'https://api.vetspire.com/graphql'


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--token-file')
    args = parser.parse_args()
    if args.token_file:
        with open(os.path.expanduser(args.token_file)) as f:
            args.token = f.read().strip()
    args.token = args.token.strip().removeprefix('Bearer ').strip()

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
    loc_fields = [f for f in qfields if 'location' in f['name'].lower()]
    print('=== Root Query fields matching "location" ===')
    for f in sorted(loc_fields, key=lambda x: x['name']):
        tname = type_name(f['type'])
        argstr = ', '.join(f"{a['name']}: {type_name(a['type'])}" for a in (f.get('args') or []))
        print(f"  {f['name']}({argstr}): {tname}")
    print()

    # Try an actual live call with a known real location vetspire id, to
    # confirm the exact shape works before wiring it into a real sync script.
    print('=== Live test: location(id) { providerSchedules } for Lincoln Park (23083) ===')
    test = gql(args.token, '''
    query($id: ID) {
      location(id: $id) {
        id
        name
        openDate
        providerSchedules(startDate: "2026-08-01", endDate: "2026-08-31") {
          id
          start
          end
          providerId
          provider { id name }
        }
      }
    }
    ''', {'id': '23083'})
    print(json.dumps(test, indent=2)[:4000])


if __name__ == '__main__':
    main()
