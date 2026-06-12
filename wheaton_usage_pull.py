#!/usr/bin/env python3
"""
Wheaton Nightly Usage Pull
Runs at midnight via cron. Pulls today's dispensed products from Vetspire usageReport
and upserts to Supabase dispensed_items table for true COGS / lot lifecycle tracking.

Token management:
  - Reads JWT from ~/.vetspire_token (same token as wheaton_revenue_pull.py)
  - Exits with instructions if token is expired
  - To refresh: copy Bearer token from Vetspire DevTools → paste here:
      python3 -c "open('/Users/meganhenley/.vetspire_token','w').write('TOKEN')"
"""

import json, urllib.request, urllib.error, os, sys, base64
from datetime import date, datetime, timezone

# ── Config ──────────────────────────────────────────────────────
VETSPIRE_ENDPOINT = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN   = "https://scoutcare.vetspire.com"
TOKEN_FILE        = os.path.expanduser("~/.vetspire_token")

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = [
    {"id": "28253", "name": "Wheaton"},
    # Add more as the pilot expands:
    # {"id": "23083", "name": "Lincoln Park"},
    # {"id": "27390", "name": "Old Orchard"},
    # {"id": "24356", "name": "West Loop"},
]

# ── Token management ─────────────────────────────────────────────
def load_token():
    if not os.path.exists(TOKEN_FILE):
        print("ERROR: No token file. Run:")
        print(f"  python3 -c \"open('{TOKEN_FILE}','w').write('YOUR_JWT_HERE')\"")
        sys.exit(1)
    return open(TOKEN_FILE).read().strip().removeprefix("Bearer ").strip()

def check_token_expiry(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = data.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        if exp < now:
            hours_ago = (now - exp) / 3600
            print(f"ERROR: Token expired {hours_ago:.1f} hours ago.")
            print("  Refresh: Open Vetspire → DevTools → Network → graphql request")
            print(f"           → Headers → Authorization → copy after 'Bearer ' → run:")
            print(f"           python3 -c \"open('{TOKEN_FILE}','w').write('NEW_TOKEN')\"")
            sys.exit(1)
        print(f"  Token valid for {(exp-now)/3600:.1f}h")
    except Exception as e:
        print(f"  (Could not decode token expiry: {e})")

# ── Vetspire GraphQL ──────────────────────────────────────────────
USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
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
    }
}
"""

def gql(token, query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Origin": VETSPIRE_ORIGIN,
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# ── Supabase REST ─────────────────────────────────────────────────
def supa_upsert(records):
    """Upsert records into dispensed_items via Supabase REST API."""
    if not records:
        return 0
    payload = json.dumps(records).encode()
    req = urllib.request.Request(
        SUPA_URL + "/rest/v1/dispensed_items",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
    )
    req.get_method = lambda: "POST"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Supabase error {e.code}: {body[:300]}")
        return e.code

# ── Main ─────────────────────────────────────────────────────────
def main():
    today = date.today().isoformat()
    print(f"\n=== Wheaton Usage Pull — {today} ===")

    token = load_token()
    check_token_expiry(token)

    total_inserted = 0

    for loc in LOCATIONS:
        print(f"\n  Pulling usageReport for {loc['name']} (ID: {loc['id']})...")

        try:
            r = gql(token, USAGE_QUERY, {
                "lids": [loc["id"]],
                "s": today,
                "e": today,
            })
        except Exception as e:
            print(f"  ERROR querying Vetspire: {e}")
            continue

        if "errors" in r:
            print(f"  API error: {r['errors'][0]['message'][:200]}")
            continue

        order_items = r.get("data", {}).get("usageReport", {}).get("orderItems", [])
        print(f"  {len(order_items)} order items returned")

        if not order_items:
            print(f"  No usage data for today.")
            continue

        # Build Supabase records
        records = []
        for item in order_items:
            prod = item.get("product") or {}
            pid  = item.get("productId") or prod.get("id")
            if not pid:
                continue

            # Parse dispensed_at from updatedAt
            updated_at = item.get("updatedAt")
            if updated_at:
                # Ensure timezone info — Vetspire returns NaiveDateTime
                if "+" not in updated_at and "Z" not in updated_at:
                    updated_at = updated_at + "Z"
            else:
                updated_at = datetime.now(timezone.utc).isoformat()

            unit_cost = prod.get("unitCost")
            sku       = prod.get("sku")

            # Skip services — only track physical inventory (must have SKU or unit cost)
            if not sku and unit_cost is None:
                continue

            unit_price_str = item.get("unitPrice", "0")
            try:
                unit_price = float(unit_price_str) if unit_price_str else 0.0
            except (ValueError, TypeError):
                unit_price = 0.0

            records.append({
                "vetspire_product_id":    pid,
                "product_name":           prod.get("name"),
                "sku":                    prod.get("sku"),
                "quantity":               float(item.get("quantity") or 0),
                "quantity_remaining":     float(item.get("quantityRemaining") or 0),
                "unit_price":             unit_price,
                "unit_cost":              float(unit_cost) if unit_cost is not None else None,
                "subtotal_cents":         int(item.get("subtotalCents") or 0),
                "total_before_tax_cents": int(item.get("totalBeforeTaxCents") or 0),
                "returned":               bool(item.get("returned", False)),
                "refunded":               bool(item.get("refunded", False)),
                "dispensed_at":           updated_at,
                "location_id":            loc["id"],
                "location_name":          loc["name"],
                "pulled_at":              datetime.now(timezone.utc).isoformat(),
            })

        if records:
            print(f"  Upserting {len(records)} records to Supabase...")
            status = supa_upsert(records)
            if str(status).startswith("2"):
                print(f"  ✓ Upserted successfully (HTTP {status})")
                total_inserted += len(records)
            else:
                print(f"  ✗ Upsert returned status {status}")

            # Show top products dispensed today
            by_product = {}
            for rec in records:
                if not rec["returned"] and not rec["refunded"]:
                    name = rec["product_name"] or rec["vetspire_product_id"]
                    by_product[name] = by_product.get(name, 0) + rec["quantity"]
            top = sorted(by_product.items(), key=lambda x: -x[1])[:10]
            print(f"\n  Top products dispensed today:")
            for name, qty in top:
                print(f"    {qty:>6.1f}  {name}")

    print(f"\n  Total records upserted: {total_inserted}")
    print("\nDone.\n")

if __name__ == "__main__":
    main()
