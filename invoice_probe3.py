#!/usr/bin/env python3
"""
Phase 3 — focus on paidSalesReport (returns [ReportRow]) and Visit type.
This is our best lead for product-level sold data.
"""

import json, urllib.request, os, base64
from datetime import datetime, timezone, date

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"
WHEATON_ID = "28253"
today      = date.today().isoformat()

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

try:
    payload = token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload))
    exp = data.get("exp", 0)
    now = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print(f"TOKEN EXPIRED"); exit(1)
    print(f"Token valid for {(exp-now)/3600:.1f}h\n")
except Exception as e:
    print(f"Could not decode token: {e}")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": "https://scoutcare.vetspire.com",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def try_query(label, query, variables=None):
    print(f"\n=== {label} ===")
    try:
        r = gql(query, variables)
        if "errors" in r:
            print(f"  ✗ {r['errors'][0]['message'][:250]}")
        else:
            print(f"  ✓")
            print(json.dumps(r.get("data"), indent=2)[:4000])
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# 1. Introspect ReportRow type
try_query("ReportRow type fields",
    '{ __type(name: "ReportRow") { fields { name description type { name kind ofType { name kind } } } } }')

# 2. paidSalesReport with all likely subfields
try_query("paidSalesReport Wheaton today — with subfields",
    """query($lids:[ID!], $s:Date, $e:Date){
        paidSalesReport(locationIds:$lids, startDate:$s, endDate:$e) {
            date location_id total quantity productName productId sku unitCost
        }
    }""",
    {"lids": [WHEATON_ID], "s": today, "e": today})

# 3. Visit type fields
try_query("Visit type fields",
    '{ __type(name: "Visit") { fields { name description type { name kind ofType { name kind } } } } }')

# 4. Try visits with product line items
try_query("visits Wheaton today — basic fields",
    """query($lid:ID!, $s:Date, $e:Date){
        visits(locationId:$lid, startDate:$s, endDate:$e, limit:2) {
            id checkedInAt paidAt total
            lineItems { id description quantity unitPrice productId }
        }
    }""",
    {"lid": WHEATON_ID, "s": today, "e": today})

# 5. visits with no subfields to see what type it returns
try_query("visits return type check",
    """query($lid:ID!, $s:Date, $e:Date){
        visits(locationId:$lid, startDate:$s, endDate:$e, limit:1) { id }
    }""",
    {"lid": WHEATON_ID, "s": today, "e": today})

# 6. Check all report-type fields (things returning ReportRow)
print("\n=== All query fields returning ReportRow ===")
r = gql("{ __schema { queryType { fields { name type { name kind ofType { name kind } } } } } }")
fields = r.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
for f in fields:
    t = f.get("type", {})
    type_name = t.get("name") or (t.get("ofType") or {}).get("name") or ""
    if "Report" in type_name or "ReportRow" in type_name:
        print(f"  {f['name']} → {type_name}")

print("\nProbe 3 complete.")
