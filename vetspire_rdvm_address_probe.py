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
    field_types = {}
    for f in fields:
        tname = f['type'].get('name') or (f['type'].get('ofType') or {}).get('name') or f['type']['kind']
        field_types[f['name']] = tname
        print(f"  {f['name']}: {tname}")
    print()

    # Known from a first run of this probe: plain-scalar address fields plus
    # a few marketing-relevant scalars worth sampling in the same pass. Kept
    # as a fixed list (not the keyword-matching first draft) because that
    # draft also caught `locations`/`primaryLocation` -- object-typed fields
    # that need their own subfield selection and broke the whole query when
    # mixed in with scalars (GraphQL fails the entire query on one bad
    # field, so the scalars never got confirmed either).
    scalar_fields = [f for f in (
        'addressLine1', 'addressLine2', 'city', 'state', 'postalCode', 'country',
        'milesAway', 'numberOfVisitsLastNinetyDays', 'numberOfTrailingYearPatients', 'lastVisitDate',
    ) if f in field_types]

    print(f'=== Sampling scalar address/marketing fields: {scalar_fields} ===')
    print('Fetching a live sample to confirm population (not just schema presence)...\n')

    field_selection = ' '.join(scalar_fields)
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
    address_fields = [f for f in scalar_fields if f in ('addressLine1', 'addressLine2', 'city', 'state', 'postalCode', 'country')]
    for r in rows:
        has_any = any(r.get(f) for f in address_fields)
        if has_any:
            populated += 1
        print(f"  {r.get('name')}: " + ', '.join(f"{f}={r.get(f)!r}" for f in scalar_fields))

    print(f'\n{populated} of {len(rows)} sample rDVMs have at least one populated address field.')

    # `visits: RdvmVisit` on Rdvm's field list is a major finding in its own
    # right -- if Vetspire already tracks rDVM visits natively, the "CRM"
    # half of the Marketing tab ask (visit logs) might already be half-built
    # on Vetspire's side rather than 100% ScoutSync-native. Introspect it.
    print("\n=== Introspecting RdvmVisit type ===")
    visit_type = gql(token, '{ __type(name: "RdvmVisit") { name fields { name type { name kind ofType { name kind } } } } }')
    if 'errors' in visit_type:
        print('GraphQL errors:', json.dumps(visit_type['errors'], indent=2))
        return
    visit_fields = (visit_type.get('data') or {}).get('__type', {}).get('fields') or []
    if not visit_fields:
        print('RdvmVisit type not found or has no fields.')
        return
    print(f'{len(visit_fields)} fields on RdvmVisit:')
    for f in visit_fields:
        tname = f['type'].get('name') or (f['type'].get('ofType') or {}).get('name') or f['type']['kind']
        print(f"  {f['name']}: {tname}")


if __name__ == '__main__':
    main()
