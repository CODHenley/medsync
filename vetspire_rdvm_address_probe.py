#!/usr/bin/env python3
"""
vetspire_rdvm_address_probe.py
Checks whether Vetspire's Rdvm type exposes any address/geography field at
all, to decide how to plot a referral-origin map on ScoutSync's upcoming
Marketing tab: the rDVM's own location (if available) vs. an approximation
from the ZIP codes of the clients each rDVM has referred (which ScoutSync
already has via clients.postal_code + referral_relationships).

Confirmed so far (vetspire_clinical_schema_probe.py): Rdvm has
id/name/isActive/tags/documents. This probe specifically introspects the
Rdvm type's full field list via GraphQL introspection, and if an address-
shaped field exists, fetches a live sample to confirm it's actually
populated (a field existing but always null is as unusable as no field at
all).

Usage:
  python3 vetspire_rdvm_address_probe.py --token-file ~/.vetspire_token
  python3 vetspire_rdvm_address_probe.py --token "eyJ..."

Report-only. No writes.
"""
import sys, json, argparse, urllib.request, urllib.error

VETSPIRE_URL = 'https://api.vetspire.com/graphql'


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    # The permanent API key (VETSPIRE_API_TOKEN) goes in raw, no "Bearer " prefix —
    # same auth pattern as vetspire_clinical_schema_probe.py / wheaton_lot_sync.py.
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


INTROSPECT_RDVM = """
{
  __type(name: "Rdvm") {
    name
    fields {
      name
      type { name kind ofType { name kind } }
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='Vetspire API token (raw, no Bearer prefix)')
    parser.add_argument('--token-file', help='Path to a file containing the token')
    args = parser.parse_args()

    token = args.token
    if args.token_file:
        with open(args.token_file) as f:
            token = f.read().strip()
    if not token:
        print('ERROR: pass --token or --token-file')
        sys.exit(1)

    print("=== Introspecting Rdvm type's full field list ===")
    result = gql(token, INTROSPECT_RDVM)
    if 'errors' in result:
        print('GraphQL errors:', json.dumps(result['errors'], indent=2))
        sys.exit(1)

    fields = (result.get('data') or {}).get('__type', {}).get('fields') or []
    if not fields:
        print('No fields returned -- Rdvm type may not exist or introspection is disabled.')
        return

    print(f"{len(fields)} fields on Rdvm:")
    address_like = []
    for f in fields:
        tname = f['type'].get('name') or (f['type'].get('ofType') or {}).get('name') or f['type']['kind']
        print(f"  {f['name']}: {tname}")
        lname = f['name'].lower()
        if any(k in lname for k in ('address', 'street', 'city', 'state', 'zip', 'postal', 'lat', 'lng', 'geo', 'location')):
            address_like.append(f['name'])

    print()
    if not address_like:
        print('=== No address/geography-shaped field found on Rdvm. ===')
        print('Recommendation: fall back to approximating rDVM location from referred clients\' ZIPs.')
        return

    print(f'=== Address-shaped field(s) found: {address_like} ===')
    print('Fetching a live sample to confirm population (not just schema presence)...\n')

    field_selection = ' '.join(address_like)
    sample_query = f"""
    {{
      rdvms(limit: 20) {{
        id
        name
        {field_selection}
      }}
    }}
    """
    sample = gql(token, sample_query)
    if 'errors' in sample:
        print('GraphQL errors on sample fetch:', json.dumps(sample['errors'], indent=2))
        return

    rows = (sample.get('data') or {}).get('rdvms') or []
    print(f'{len(rows)} sample rDVMs fetched:')
    populated = 0
    for r in rows:
        has_any = any(r.get(f) for f in address_like)
        if has_any:
            populated += 1
        print(f"  {r.get('name')}: " + ', '.join(f"{f}={r.get(f)!r}" for f in address_like))

    print(f'\n{populated} of {len(rows)} sample rDVMs have at least one populated address-like field.')


if __name__ == '__main__':
    main()
