#!/usr/bin/env python3
"""
check_date_attribution.py
Read-only. Vetspire's usageReport(startDate,endDate) may bucket order items
by a field other than the `updatedAt` we store as dispensed_at (e.g. a
service/encounter date vs a last-modified timestamp). If so, an item
Vetspire attributes to this window could exist in Supabase already, just
filed under a different dispensed_at outside this window — showing up as
"missing" in a date-filtered comparison when it's actually just misdated,
not absent.

For every Vetspire order item in range with product.sku is null (the
bucket where diagnose_reconciliation_gap.py found the biggest imbalance),
looks each one up in Supabase BY order_item_id alone (no date filter) and
reports whether it exists, and if so what dispensed_at it's stored under.
"""
import argparse, json, os, urllib.request

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems {
            id
            productId
            product { id name sku }
            quantity
            returned
            refunded
            updatedAt
        }
    }
}
"""


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if token:
        return token.removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set.")


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
        "Origin":        VETSPIRE_ORIGIN,
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def supa_get(order_item_id, location_id):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/dispensed_items"
        f"?select=id,dispensed_at,pulled_at,quantity"
        f"&order_item_id=eq.{order_item_id}&location_id=eq.{location_id}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    token = load_token()
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.start, "e": args.end})
    if "errors" in result:
        print(f"ERROR: {result['errors']}"); return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])

    no_sku_items = [it for it in order_items
                    if not it.get("returned") and not it.get("refunded")
                    and (it.get("productId") or (it.get("product") or {}).get("id"))
                    and not (it.get("product") or {}).get("sku")]
    print(f"Vetspire order items in range with no SKU (excl ret/ref): {len(no_sku_items)}")

    checked = 0
    found_in_window = 0
    found_outside_window = 0
    not_found = 0
    for it in no_sku_items[:args.limit]:
        oid = it.get("id")
        rows = supa_get(oid, args.location)
        checked += 1
        if not rows:
            not_found += 1
            print(f"  MISSING  id={oid} updatedAt={it.get('updatedAt')} qty={it.get('quantity')}")
        else:
            row = rows[0]
            row_date = (row.get("dispensed_at") or "")[:10]
            in_window = args.start <= row_date <= args.end
            if in_window:
                found_in_window += 1
            else:
                found_outside_window += 1
                print(f"  MISDATED id={oid}  vetspire_updatedAt={it.get('updatedAt')}  "
                      f"stored_dispensed_at={row.get('dispensed_at')}  (outside {args.start}..{args.end})")

    print(f"\nChecked {checked} of {len(no_sku_items)} no-SKU items:")
    print(f"  found, correctly in window: {found_in_window}")
    print(f"  found, but stored OUTSIDE this window (misdated): {found_outside_window}")
    print(f"  not found in Supabase at all (genuinely missing): {not_found}")


if __name__ == "__main__":
    main()
