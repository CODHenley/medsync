#!/usr/bin/env python3
"""
Phase 7 — correct usageReport query using proper nested fields,
plus get MedicationsFilledReportItem / MedicationsReportItem field lists.
"""

import json, urllib.request, os, base64
from datetime import datetime, timezone, date

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"
WHEATON_ID = "28253"
today      = date.today().isoformat()
month_start = today[:8] + "01"

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()
try:
    payload = token.split(".")[1] + "=="
    data = json.loads(base64.urlsafe_b64decode(payload))
    exp = data.get("exp", 0)
    now = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print("TOKEN EXPIRED"); exit(1)
    print(f"Token valid for {(exp-now)/3600:.1f}h\n")
except Exception as e:
    print(f"Token decode error: {e}")

def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": "https://scoutcare.vetspire.com",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def introspect_type(type_name):
    print(f"\n=== {type_name} fields ===")
    r = gql(f'{{ __type(name: "{type_name}") {{ fields {{ name description type {{ name kind ofType {{ name kind }} }} }} }} }}')
    t = r.get("data", {}).get("__type")
    if t and t.get("fields"):
        for f in t["fields"]:
            t2 = f["type"]
            type_str = t2.get("name") or f"{t2.get('kind')}({(t2.get('ofType') or {}).get('name','')})"
            print(f"  {f['name']}: {type_str}")
    else:
        print(f"  (not found: {r})")

def try_query(label, query, variables=None):
    print(f"\n=== {label} ===")
    try:
        r = gql(query, variables)
        if "errors" in r:
            print(f"  ✗ {r['errors'][0]['message'][:300]}")
        else:
            print(f"  ✓")
            print(json.dumps(r.get("data"), indent=2)[:8000])
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# ── Get MedicationsFilledReportItem and MedicationsReportItem fields ──────────
introspect_type("MedicationsFilledReportItem")
introspect_type("MedicationsReportItem")

# ── usageReport with CORRECT nested product field ────────────────────────────
try_query("usageReport this month — CORRECT query",
    """query($lids:[ID!], $s:Date, $e:Date){
        usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
            orderItems {
                productId
                product { id name sku unitCost }
                quantity
                quantityRemaining
                unitPrice
                subtotalCents
                totalBeforeTaxCents
                returned
                refunded
                updatedAt
            }
            totals {
                id
                name
                totalQuantity
                totalSpend
            }
        }
    }""",
    {"lids": [WHEATON_ID], "s": month_start, "e": today})

print("\nProbe 7 complete.")
