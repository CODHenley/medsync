#!/usr/bin/env python3
"""
Probe Vetspire GraphQL for invoice / line item / product-dispensed fields.
Helps us find the data needed for lot lifecycle / true COGS tracking.
"""

import json, urllib.request, os, base64
from datetime import datetime, timezone, date

TOKEN_FILE = os.path.expanduser("~/.vetspire_token")
ENDPOINT   = "https://api.vetspire.com/graphql"

token = open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

# Check expiry
try:
    payload = token.split(".")[1]
    payload += "=" * (4 - len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload))
    exp = data.get("exp", 0)
    now = datetime.now(timezone.utc).timestamp()
    if exp < now:
        print(f"TOKEN EXPIRED {(now-exp)/3600:.1f}h ago — refresh it first"); exit(1)
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

# ── 1. Scan all query fields for relevant keywords ─────────────────────────
print("=== Query fields matching invoice / line item / product ===")
r = gql("{ __schema { queryType { fields { name description } } } }")
fields = r.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])

keywords = ["invoice","line","item","product","dispensed","sold","transaction",
            "charge","receipt","visit","order","encounter","service","client","patient"]
matches = []
for f in fields:
    name = f.get("name","").lower()
    desc = (f.get("description") or "").lower()
    if any(k in name or k in desc for k in keywords):
        matches.append(f["name"])
        print(f"  ★ {f['name']}: {(f.get('description') or '')[:120]}")

print(f"\n  {len(matches)} matches out of {len(fields)} total fields\n")

# ── 2. Get args for the most promising candidates ──────────────────────────
CANDIDATES = ["invoices", "invoice", "lineItems", "lineItem", "invoiceLineItems",
              "clientInvoices", "patientInvoices", "visits", "encounter",
              "transactions", "charges", "products", "dispensedProducts",
              "paidInvoices", "invoicesByLocation"] + matches[:10]
CANDIDATES = list(dict.fromkeys(CANDIDATES))  # dedupe

print("=== Args for promising candidates ===")
r2 = gql("{ __schema { queryType { fields { name args { name type { name kind ofType { name kind } } } } } } }")
all_fields = r2.get("data",{}).get("__schema",{}).get("queryType",{}).get("fields",[])
for f in all_fields:
    if f["name"] in CANDIDATES:
        args = f.get("args",[])
        arg_str = ", ".join(a["name"] for a in args) if args else "(no args)"
        print(f"  {f['name']}: {arg_str}")

# ── 3. Try invoices query for today ───────────────────────────────────────
today = date.today().isoformat()
print(f"\n=== Attempting invoices query for Wheaton (today: {today}) ===")

attempts = [
    ("invoices with locationId + date", {
        "query": "query($lid:ID!, $s:Date, $e:Date){ invoices(locationId:$lid, startDate:$s, endDate:$e) { id total paidAt lineItems { id description quantity unitPrice } } }",
        "variables": {"lid": "28253", "s": today, "e": today}
    }),
    ("invoices no subfields", {
        "query": "query($lid:ID!, $s:Date, $e:Date){ invoices(locationId:$lid, startDate:$s, endDate:$e) }",
        "variables": {"lid": "28253", "s": today, "e": today}
    }),
    ("invoices locationIds array", {
        "query": "query($lids:[ID!], $s:Date, $e:Date){ invoices(locationIds:$lids, startDate:$s, endDate:$e) }",
        "variables": {"lids": ["28253"], "s": today, "e": today}
    }),
]

for label, payload in attempts:
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(ENDPOINT, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Origin": "https://scoutcare.vetspire.com",
        })
        r = json.loads(urllib.request.urlopen(req, timeout=20).read())
        if "errors" not in r:
            print(f"  ✓ {label}:")
            print(json.dumps(r.get("data"), indent=2)[:3000])
            break
        else:
            print(f"  ✗ {label}: {r['errors'][0]['message'][:150]}")
    except Exception as e:
        print(f"  ✗ {label}: {e}")

print("\nProbe complete.")
