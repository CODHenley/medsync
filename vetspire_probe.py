#!/usr/bin/env python3
"""
Probe Vetspire GraphQL — tries multiple endpoints and auth formats.
"""
import json, urllib.request, urllib.error

TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ2ZXRzcGlyZSIsImV4cCI6MTc4MTMwMjQ0MiwiaWF0IjoxNzgxMjE2MDQyLCJpc3MiOiJ2ZXRzcGlyZSIsImp0aSI6ImYyZjRhODNlLTZjZjctNGVhOS1hNmEyLWU5M2FmMjJiZGUxNyIsIm5iZiI6MTc4MTIxNjA0MSwicHJvdmlkZXIiOnsiaWQiOjYzODk5OCwiaXNfb3JnX2FkbWluIjp0cnVlLCJpc192ZXRlcmluYXJpYW4iOmZhbHNlLCJvcmdfaWQiOjI3MCwidGVuYW50X2lkIjoiZGVmYXVsdCJ9LCJzdWIiOiJQcm92aWRlcjo2Mzg5OTgiLCJzdXBwb3J0X3VzZXIiOm51bGwsInR5cCI6InRva2VuIn0.CAUpc1XKl9tdCoR88rDBSA3B4FpkEYicnN15STsdauH0pfPtpTFZVVvVh9VIsSiQy5kMR7_Y-CeAUqzJhC6I1w"
ENDPOINT = "https://api.vetspire.com/graphql"

def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
            "Origin": "https://scoutcare.vetspire.com",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# 1. Confirm connection
print("=== Connection test ===")
try:
    r = gql("{ __typename }")
    print(f"OK: {r}")
except Exception as e:
    print(f"FAILED: {e}")

# 2. Introspect for revenue/invoice queries
print("\n=== Revenue-related queries ===")
try:
    r = gql("{ __schema { queryType { fields { name description } } } }")
    fields = r.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
    revenue_kw = ["revenue","invoice","transaction","finance","payment","sale","charge","receipt","billing","total"]
    for f in fields:
        name = f.get("name", "")
        if any(k in name.lower() for k in revenue_kw):
            print(f"  ★ {name}: {f.get('description','')}")
    print(f"\n  (Total query fields: {len(fields)})")
except Exception as e:
    print(f"FAILED: {e}")

from datetime import date
today = date.today().isoformat()
WHEATON_ID = "28253"

# 3. Introspect args for revenue-candidate fields
CANDIDATES = ["salesReport", "paidSalesReport", "paymentsTotals", "revenueCenters", "ledgerEntryTotals", "payments"]
print(f"\n=== Args for revenue candidates ===")
try:
    r = gql("{ __schema { queryType { fields { name args { name type { name kind ofType { name kind } } } } } } }")
    fields = r.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])
    for f in fields:
        if f["name"] in CANDIDATES:
            args = f.get("args", [])
            arg_str = ", ".join(a["name"] for a in args) if args else "(no args)"
            print(f"  {f['name']}: {arg_str}")
except Exception as e:
    print(f"FAILED: {e}")

# 4. salesReport with correct args (returns raw JSON, no subfields)
print(f"\n=== salesReport for Wheaton ({today}) ===")
queries = [
    ("locationIds array + dates",
     {"query": "query($lids:[ID!], $s:Date, $e:Date){ salesReport(locationIds:$lids, startDate:$s, endDate:$e) }",
      "variables": {"lids": [WHEATON_ID], "s": today, "e": today}}),
    ("locationIds array only",
     {"query": "query($lids:[ID!]){ salesReport(locationIds:$lids) }",
      "variables": {"lids": [WHEATON_ID]}}),
    ("no args",
     {"query": "{ salesReport }",
      "variables": {}}),
]
for label, payload in queries:
    try:
        req = urllib.request.Request(
            ENDPOINT,
            json.dumps(payload).encode(),
            {"Content-Type": "application/json",
             "Authorization": f"Bearer {TOKEN}",
             "Origin": "https://scoutcare.vetspire.com"}
        )
        r = json.loads(urllib.request.urlopen(req, timeout=15).read())
        if "errors" not in r:
            print(f"  ✓ {label}:")
            print(json.dumps(r.get("data"), indent=2)[:2000])
            break
        else:
            print(f"  ✗ {label}: {r['errors'][0]['message'][:120]}")
    except Exception as e:
        print(f"  ✗ {label}: {e}")

# 4. Try locations to find Wheaton ID
print("\n=== Locations ===")
try:
    r = gql("{ locations { id name } }")
    print(json.dumps(r.get("data"), indent=2))
except Exception as e:
    print(f"FAILED: {e}")

print("\nProbe complete.")
