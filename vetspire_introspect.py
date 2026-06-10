"""
vetspire_introspect.py
Find the correct field names for inventory thresholds on Vetspire's Product type.
Usage: python3 vetspire_introspect.py --token YOUR_TOKEN
"""
import sys, json, argparse, urllib.request

VETSPIRE_URL = 'https://api.vetspire.com/graphql'

def gql(token, query):
    payload = json.dumps({'query': query}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

parser = argparse.ArgumentParser()
parser.add_argument('--token', required=False)
parser.add_argument('--token-file', required=False)
args = parser.parse_args()

if args.token_file:
    import os
    with open(os.path.expanduser(args.token_file)) as f:
        args.token = f.read().strip()
if not args.token:
    print('ERROR: provide --token or --token-file')
    raise SystemExit(1)

print('=== Product type fields ===')
r = gql(args.token, '{ __type(name: "Product") { fields { name type { name kind ofType { name } } } } }')
fields = r.get('data', {}).get('__type', {}).get('fields', [])
for f in sorted(fields, key=lambda x: x['name']):
    t = f['type']
    tname = t.get('name') or (t.get('ofType') or {}).get('name') or t.get('kind')
    if any(kw in f['name'].lower() for kw in ['threshold','stock','quantity','inventory','min','max','reorder']):
        print(f"  *** {f['name']}: {tname}")
    else:
        print(f"  {f['name']}: {tname}")

print()
print('=== Query type — look for threshold/inventory queries ===')
r2 = gql(args.token, '{ __type(name: "Query") { fields { name } } }')
qfields = r2.get('data', {}).get('__type', {}).get('fields', [])
for f in qfields:
    if any(kw in f['name'].lower() for kw in ['threshold','stock','inventory','low']):
        print(f"  *** {f['name']}")
    else:
        print(f"  {f['name']}")
