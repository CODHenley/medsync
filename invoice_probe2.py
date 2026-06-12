#!/usr/bin/env python3
"""
Phase 2 probe — dig into visits, inCollections, invoiceLineItem* fields
and find the sold/dispensed product data for lot lifecycle tracking.
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
        print(f"TOKEN EXPIRED — refresh it"); exit(1)
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
    print(f"\n--- {label} ---")
    try:
        r = gql(query, variables)
        if "errors" in r:
            print(f"  ✗ {r['errors'][0]['message'][:200]}")
        else:
            print(f"  ✓ Result:")
            print(json.dumps(r.get("data"), indent=2)[:3000])
    except Exception as e:
        print(f"  ✗ Exception: {e}")

# ── 1. Get ALL fields with "invoic" in the name ─────────────────────────────
print("=== All fields containing 'invoic' ===")
r = gql("{ __schema { queryType { fields { name description } } } }")
fields = r.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
for f in fields:
    if "invoic" in f["name"].lower():
        print(f"  {f['name']}: {(f.get('description') or '')[:120]}")

# ── 2. Get args for visit, visits, inCollections, invoiceLineItem* ──────────
print("\n=== Args for visit / visits / inCollections / invoiceLineItem* ===")
r2 = gql("{ __schema { queryType { fields { name args { name type { name kind ofType { name kind } } } } } } }")
all_fields = r2.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
targets = ["visit", "visits", "inCollections", "invoiceLineItemReasons",
           "invoiceLineItems", "paidInvoicesReport", "invoiceReport",
           "invoicesReport", "clientInvoice", "visitLineItems"]
for f in all_fields:
    name = f["name"]
    if name in targets or "invoic" in name.lower() or name in ["visit","visits"]:
        args = f.get("args",[])
        arg_str = ", ".join(a["name"] for a in args) if args else "(no args)"
        print(f"  {name}: {arg_str}")

# ── 3. Introspect the Visit type — what fields does a visit have? ────────────
print("\n=== Visit type fields ===")
try_query("Visit type introspection",
    "{ __type(name: \"Visit\") { fields { name description type { name kind ofType { name kind } } } } }")

# ── 4. Try visits query for Wheaton today ───────────────────────────────────
try_query("visits for Wheaton today (basic)",
    "query($lid:ID!, $s:Date, $e:Date){ visits(locationId:$lid, startDate:$s, endDate:$e, limit:3) { id checkedInAt total } }",
    {"lid": WHEATON_ID, "s": today, "e": today})

try_query("visits no subfields",
    "query($lid:ID!, $s:Date, $e:Date){ visits(locationId:$lid, startDate:$s, endDate:$e, limit:3) }",
    {"lid": WHEATON_ID, "s": today, "e": today})

# ── 5. Try inCollections ─────────────────────────────────────────────────────
try_query("inCollections",
    "{ inCollections { id } }")

# ── 6. Try invoiceLineItemReasons ────────────────────────────────────────────
try_query("invoiceLineItemReasons",
    "{ invoiceLineItemReasons { id name } }")

# ── 7. Introspect InvoiceLineItem type ───────────────────────────────────────
try_query("InvoiceLineItem type introspection",
    "{ __type(name: \"InvoiceLineItem\") { fields { name description type { name kind ofType { name kind } } } } }")

# ── 8. Introspect InvoiceLineItemReason type ─────────────────────────────────
try_query("InvoiceLineItemReason type introspection",
    "{ __type(name: \"InvoiceLineItemReason\") { fields { name description type { name kind ofType { name kind } } } } }")

# ── 9. Check if paidSalesReport has line-item breakdown ──────────────────────
try_query("paidSalesReport for Wheaton today",
    "query($lids:[ID!], $s:Date, $e:Date){ paidSalesReport(locationIds:$lids, startDate:$s, endDate:$e) }",
    {"lids": [WHEATON_ID], "s": today, "e": today})

print("\n\nProbe 2 complete.")
