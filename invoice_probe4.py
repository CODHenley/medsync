#!/usr/bin/env python3
"""
Phase 4 — target medicationsFilledReport, medicationsReport, usageReport, grossSalesReport.
These are the most likely sources for product-level sold/dispensed data.
"""

import json, urllib.request, os, base64
from datetime import datetime, timezone, date

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"
WHEATON_ID = "28253"
today      = date.today().isoformat()

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
            print(f"  ✗ {r['errors'][0]['message'][:250]}")
        else:
            print(f"  ✓")
            print(json.dumps(r.get("data"), indent=2)[:5000])
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# ── Get args for our target reports ─────────────────────────────────────────
print("=== Args for target report fields ===")
r = gql("{ __schema { queryType { fields { name args { name type { name kind ofType { name kind } } } } } } }")
all_fields = r.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
targets = ["medicationsFilledReport", "medicationsReport", "usageReport",
           "grossSalesReport", "salesTypedReport", "paidSalesReport", "ReportRow"]
for f in all_fields:
    if f["name"] in targets:
        args = f.get("args",[])
        arg_str = ", ".join(a["name"] for a in args) if args else "(no args)"
        print(f"  {f['name']}: {arg_str}")

# ── Introspect return types ───────────────────────────────────────────────────
for type_name in ["MedicationsFilledReportResult", "MedicationsReportResult",
                  "UsageReport", "ReportRow"]:
    try_query(f"{type_name} type fields",
        f'{{ __type(name: "{type_name}") {{ fields {{ name description type {{ name kind ofType {{ name kind }} }} }} }} }}')

# ── Try medicationsFilledReport ───────────────────────────────────────────────
try_query("medicationsFilledReport args check",
    "query($lids:[ID!], $s:Date, $e:Date){ medicationsFilledReport(locationIds:$lids, startDate:$s, endDate:$e) }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

# ── Try medicationsReport ─────────────────────────────────────────────────────
try_query("medicationsReport args check",
    "query($lids:[ID!], $s:Date, $e:Date){ medicationsReport(locationIds:$lids, startDate:$s, endDate:$e) }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

# ── Try usageReport ───────────────────────────────────────────────────────────
try_query("usageReport args check",
    "query($lids:[ID!], $s:Date, $e:Date){ usageReport(locationIds:$lids, startDate:$s, endDate:$e) }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

# ── Try grossSalesReport with subfields ───────────────────────────────────────
try_query("grossSalesReport Wheaton today",
    "query($lids:[ID!], $s:Date, $e:Date){ grossSalesReport(locationIds:$lids, startDate:$s, endDate:$e) { date location_id total quantity } }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

# ── Try paidSalesReport with subfields ────────────────────────────────────────
try_query("paidSalesReport Wheaton today — with subfields",
    "query($lids:[ID!], $s:Date, $e:Date){ paidSalesReport(locationIds:$lids, startDate:$s, endDate:$e) { date location_id total } }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

print("\nProbe 4 complete.")
