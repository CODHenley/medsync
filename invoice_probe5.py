#!/usr/bin/env python3
"""
Phase 5 — get the actual subfields for medicationsFilledReport, medicationsReport,
usageReport and try calling them with real data.
"""

import json, urllib.request, os, base64
from datetime import datetime, timezone, date

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"
WHEATON_ID = "28253"
today      = date.today().isoformat()
# Also try a wider range in case today has no data yet
this_month_start = today[:8] + "01"

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

# ── 1. Deeply introspect all 3 return types ──────────────────────────────────
for type_name in ["MedicationsFilledReportResult", "MedicationsReportResult", "UsageReport"]:
    print(f"\n=== {type_name} — full field list ===")
    r = gql(f'{{ __type(name: "{type_name}") {{ fields {{ name description type {{ name kind ofType {{ name kind }} }} }} }} }}')
    t = r.get("data", {}).get("__type")
    if t and t.get("fields"):
        for f in t["fields"]:
            t2 = f["type"]
            type_str = t2.get("name") or f"{t2.get('kind')}({(t2.get('ofType') or {}).get('name','')})"
            print(f"  {f['name']}: {type_str}  — {f.get('description') or ''}")
    else:
        print(f"  (no fields or type not found: {r})")

# ── 2. Get args for these 3 reports ──────────────────────────────────────────
print("\n=== Args for medications/usage reports ===")
r = gql("{ __schema { queryType { fields { name args { name type { name kind ofType { name kind } } } } } } }")
all_fields = r.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
for f in all_fields:
    if f["name"] in ["medicationsFilledReport", "medicationsReport", "usageReport"]:
        args = f.get("args",[])
        arg_str = ", ".join(a["name"] for a in args) if args else "(no args)"
        print(f"  {f['name']}: {arg_str}")

# ── 3. Now try the queries with correct subfields ────────────────────────────
# medicationsFilledReport — try common field names
try_query("medicationsFilledReport this month",
    """query($lids:[ID!], $s:Date, $e:Date){
        medicationsFilledReport(locationIds:$lids, startDate:$s, endDate:$e) {
            date locationId productId productName sku quantity unitCost total
        }
    }""",
    {"lids": [WHEATON_ID], "s": this_month_start, "e": today})

# medicationsReport
try_query("medicationsReport this month",
    """query($lids:[ID!], $s:Date, $e:Date){
        medicationsReport(locationIds:$lids, startDate:$s, endDate:$e) {
            date locationId productId productName sku quantity unitCost total
        }
    }""",
    {"lids": [WHEATON_ID], "s": this_month_start, "e": today})

# usageReport
try_query("usageReport this month",
    """query($lids:[ID!], $s:Date, $e:Date){
        usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
            date locationId productId productName quantity unitCost total
        }
    }""",
    {"lids": [WHEATON_ID], "s": this_month_start, "e": today})

print("\nProbe 5 complete.")
