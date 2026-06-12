#!/usr/bin/env python3
"""
Phase 6 — introspect MedicationsFilledReportItem, MedicationsReportItem,
OrderItem, UsageReportTotals and then pull real data.
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
        return [f["name"] for f in t["fields"]]
    else:
        print(f"  (not found)")
        return []

def try_query(label, query, variables=None):
    print(f"\n=== {label} ===")
    try:
        r = gql(query, variables)
        if "errors" in r:
            print(f"  ✗ {r['errors'][0]['message'][:300]}")
        else:
            print(f"  ✓")
            print(json.dumps(r.get("data"), indent=2)[:6000])
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# ── Introspect item types ────────────────────────────────────────────────────
introspect_type("MedicationsFilledReportItem")
introspect_type("MedicationsReportItem")
introspect_type("OrderItem")
introspect_type("UsageReportTotals")

# ── medicationsFilledReport — uses dateFilledStart/dateFilledEnd ─────────────
try_query("medicationsFilledReport this month — nested medications",
    """query($lids:[ID!], $s:Date, $e:Date){
        medicationsFilledReport(locationIds:$lids, dateFilledStart:$s, dateFilledEnd:$e, limit:5) {
            totalCount
            medications {
                id productId productName sku quantity unitCost total dateFilled patientName clientName locationId
            }
        }
    }""",
    {"lids": [WHEATON_ID], "s": month_start, "e": today})

# ── medicationsReport — uses startDate/endDate ───────────────────────────────
try_query("medicationsReport this month — nested medications",
    """query($lids:[ID!], $s:Date, $e:Date){
        medicationsReport(locationIds:$lids, startDate:$s, endDate:$e, limit:5) {
            totalCount
            medications {
                id productId productName sku quantity unitCost total visitDate patientName locationId
            }
        }
    }""",
    {"lids": [WHEATON_ID], "s": month_start, "e": today})

# ── usageReport — uses startDate/endDate ─────────────────────────────────────
try_query("usageReport this month — orderItems",
    """query($lids:[ID!], $s:Date, $e:Date){
        usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
            orderItems {
                id productId productName sku quantity unitCost total date locationId
            }
            totals { productId productName quantity unitCost total }
        }
    }""",
    {"lids": [WHEATON_ID], "s": month_start, "e": today})

print("\nProbe 6 complete.")
