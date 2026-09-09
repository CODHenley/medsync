#!/usr/bin/env python3
"""
vetspire_rdvm_visit_mutation_probe.py
Before building a sync script that calls Vetspire's createRdvmVisit
mutation, confirms its exact input shape (required args, input object
field names/types) live -- RdvmVisit's OUTPUT type was already confirmed
(id/rdvmId/visitDate/visitType/visitRating/notes/provider/createdBy/
rdvmContact/comments/insertedAt/updatedAt), but a mutation's input args
are a separate schema object and must not be guessed.

Usage:
  python3 vetspire_rdvm_visit_mutation_probe.py --token-file ~/.vetspire_token
  python3 vetspire_rdvm_visit_mutation_probe.py --token "eyJ..."

Report-only. No writes -- introspection only, this never calls the
mutation itself.
"""
import sys, json, argparse, urllib.request

VETSPIRE_URL = 'https://api.vetspire.com/graphql'


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def describe_type(t):
    if not t:
        return 'null'
    if t.get('kind') == 'NON_NULL':
        return describe_type(t.get('ofType')) + '!'
    if t.get('kind') == 'LIST':
        return '[' + describe_type(t.get('ofType')) + ']'
    return t.get('name') or t.get('kind')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--token-file')
    args = parser.parse_args()
    token = args.token
    if args.token_file:
        with open(args.token_file) as f:
            token = f.read().strip()
    if not token:
        print('ERROR: pass --token or --token-file')
        sys.exit(1)

    # Urgent, unrelated-to-visits bug fix riding along on this same probe
    # dispatch: the just-shipped Marketing tab shows "rDVM <id>" instead of
    # real hospital names for most high-revenue rDVMs, and the map shows no
    # postal codes at all. Root cause: referral_relationships only gets a
    # row for rDVMs linked to a client with a RECENT encounter (vetspire_
    # clinical_sync.py's 3-day rolling lookback), but rdvm_revenue_daily
    # covers a full year via salesReport -- most of those rDVMs were never
    # captured. Fix: a standalone rdvm directory synced straight from
    # Vetspire's `rdvms` query, independent of any client/encounter
    # activity. Confirming its pagination args here before building that
    # sync (limit-only vs limit+offset vs cursor-based).
    print('=== Introspecting rdvms query args (for a standalone rDVM directory sync) ===')
    q_result = gql(token, '{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name kind } } } } } } } }')
    if 'errors' in q_result:
        print('GraphQL errors:', json.dumps(q_result['errors'], indent=2))
    else:
        q_fields = ((q_result.get('data') or {}).get('__schema') or {}).get('queryType', {}).get('fields') or []
        rdvms_field = next((f for f in q_fields if f['name'] == 'rdvms'), None)
        if rdvms_field:
            for a in rdvms_field['args']:
                print(f"  {a['name']}: {describe_type(a['type'])}")
        else:
            print('  rdvms query field not found')
    print()
    print('=== Live pagination test: rdvms(limit: 5, offset: 5) ===')
    page_test = gql(token, '{ rdvms(limit: 5, offset: 5) { id name } }')
    print(json.dumps(page_test, indent=2)[:1000])
    print()

    # Find createRdvmVisit's own arg list on the root mutation type.
    print('=== Introspecting createRdvmVisit mutation args ===')
    result = gql(token, """
    {
      __schema {
        mutationType {
          fields(includeDeprecated: true) {
            name
            args { name type { name kind ofType { name kind ofType { name kind } } } }
          }
        }
      }
    }
    """)
    if 'errors' in result:
        print('GraphQL errors:', json.dumps(result['errors'], indent=2))
        sys.exit(1)

    fields = ((result.get('data') or {}).get('__schema') or {}).get('mutationType', {}).get('fields') or []
    target = next((f for f in fields if f['name'] in ('createRdvmVisit', 'updateRdvmVisit')), None)
    create_field = next((f for f in fields if f['name'] == 'createRdvmVisit'), None)
    update_field = next((f for f in fields if f['name'] == 'updateRdvmVisit'), None)

    input_type_names = set()
    for label, field in (('createRdvmVisit', create_field), ('updateRdvmVisit', update_field)):
        if not field:
            print(f'{label}: NOT FOUND')
            continue
        print(f'\n{label} args:')
        for a in field['args']:
            tname = describe_type(a['type'])
            print(f"  {a['name']}: {tname}")
            # Collect the bare (non-list/non-null) type name to introspect further.
            t = a['type']
            while t and t.get('kind') in ('NON_NULL', 'LIST'):
                t = t.get('ofType')
            if t and t.get('name'):
                input_type_names.add(t['name'])

    # Introspect each distinct input object type's own fields (e.g.
    # CreateRdvmVisitInput), since the mutation itself likely takes one
    # wrapping input object rather than flat scalar args.
    for type_name in sorted(input_type_names):
        if type_name in ('ID', 'String', 'Int', 'Boolean', 'Float', 'DateTime', 'NaiveDateTime', 'Date'):
            continue
        print(f'\n=== Introspecting input type: {type_name} ===')
        t_result = gql(token, f'{{ __type(name: "{type_name}") {{ name kind inputFields {{ name type {{ name kind ofType {{ name kind }} }} }} }} }}')
        if 'errors' in t_result:
            print('GraphQL errors:', json.dumps(t_result['errors'], indent=2))
            continue
        t_data = (t_result.get('data') or {}).get('__type')
        if not t_data or not t_data.get('inputFields'):
            print(f'  (not an input object type, or has no fields -- kind={t_data.get("kind") if t_data else "unknown"})')
            continue
        for f in t_data['inputFields']:
            print(f"  {f['name']}: {describe_type(f['type'])}")


if __name__ == '__main__':
    main()
