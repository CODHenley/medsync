#!/usr/bin/env python3
"""
scoutsync_uncategorized_services_probe.py
One-off, read-only probe answering two questions from the user:

1. What are the actual highest-volume/highest-revenue "Uncategorized"
   services (dispensed_items.product_category_id is null), so real
   category recommendations can be based on real names -- not guesses?
   Cross-referenced against the 18 real category names already synced
   into product_categories, over the same trailing-90-day window the
   dashboard commonly uses.

2. Does Vetspire's GraphQL API expose ANY mutation that could write a
   product's category back to Vetspire (a prerequisite for ScoutSync ever
   auto-categorizing from the dashboard)? Introspects the real Mutation
   root type live -- this has never been checked in this repo before,
   only the Query side has ever been introspected.

Read-only: a schema introspection query and SELECTs against Supabase.
Never calls a mutation. Deleted once its purpose is served.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_uncategorized_services_probe.py
"""
import json, os, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

DAYS = 90

MUTATION_INTROSPECTION_QUERY = """
{
  __schema {
    mutationType {
      name
      fields {
        name
        description
        args { name type { kind name ofType { kind name } } }
      }
    }
  }
}
"""


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": token,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:500]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        page = supa_get(path, f"{params}&limit={page_size}&offset={offset}")
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip().removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    # ── Part 1: real uncategorized services, ranked by revenue ──
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    print(f"=== Part 1: Uncategorized services, trailing {DAYS} days (since {since}) ===\n")

    categories = supa_get("product_categories", "select=id,name&order=name.asc")
    print(f"-- {len(categories)} existing categories --")
    for c in categories:
        print(f"  {c['id']}: {c['name']}")

    uncategorized = supa_get_all(
        "dispensed_items",
        f"select=product_name,subtotal_cents&product_category_id=is.null&dispensed_at=gte.{since}",
    )
    print(f"\n-- {len(uncategorized)} uncategorized order-item rows in this window --")

    by_service = {}
    for r in uncategorized:
        name = r.get("product_name") or "(blank product name)"
        s = by_service.setdefault(name, {"count": 0, "revenue": 0.0})
        s["count"] += 1
        s["revenue"] += (r.get("subtotal_cents") or 0) / 100.0

    ranked = sorted(by_service.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    print(f"-- Top 40 uncategorized services by revenue (of {len(ranked)} distinct names) --")
    for name, s in ranked[:40]:
        print(f"  {s['count']:>5}x  ${s['revenue']:>10,.2f}   {name}")

    # ── Part 2: does Vetspire expose ANY write path for a product's category? ──
    print(f"\n=== Part 2: Vetspire Mutation root -- live introspection ===\n")
    result = gql(token, MUTATION_INTROSPECTION_QUERY)
    if "errors" in result:
        print("INTROSPECTION ERRORS:")
        print(json.dumps(result["errors"], indent=2)[:2000])
        return

    mutation_type = ((result.get("data") or {}).get("__schema") or {}).get("mutationType")
    if not mutation_type:
        print("No mutationType at all -- this API may be query-only (no mutations exposed whatsoever).")
        return

    fields = mutation_type.get("fields") or []
    print(f"Mutation root type: {mutation_type.get('name')} -- {len(fields)} total mutations exposed\n")

    product_related = [f for f in fields if "product" in f["name"].lower()]
    print(f"-- {len(product_related)} mutations with 'product' in the name --")
    for f in product_related:
        arg_str = ", ".join(
            f"{a['name']}: {(a['type'].get('ofType') or {}).get('name') or a['type'].get('name')}"
            for a in (f.get("args") or [])
        )
        print(f"  {f['name']}({arg_str})")
        if f.get("description"):
            print(f"      \"{f['description']}\"")

    category_related = [f for f in fields if "categor" in f["name"].lower()]
    print(f"\n-- {len(category_related)} mutations with 'categor' in the name --")
    for f in category_related:
        arg_str = ", ".join(
            f"{a['name']}: {(a['type'].get('ofType') or {}).get('name') or a['type'].get('name')}"
            for a in (f.get("args") or [])
        )
        print(f"  {f['name']}({arg_str})")
        if f.get("description"):
            print(f"      \"{f['description']}\"")

    if not product_related and not category_related:
        print("\nNo product- or category-named mutation found. Full mutation list, for manual review:")
        for f in fields:
            print(f"  {f['name']}")


if __name__ == "__main__":
    main()
