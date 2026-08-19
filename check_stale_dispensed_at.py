#!/usr/bin/env python3
"""
check_stale_dispensed_at.py
Read-only. Tests whether Supabase's dispensed_at goes stale after Vetspire
later updates an order item (e.g. a return/adjustment processed after our
initial capture, which changes Vetspire's updatedAt but our stored
dispensed_at is never refreshed unless something re-syncs that exact item).

For every order_item_id Supabase has stored with dispensed_at in the given
window, re-queries Vetspire over a MUCH WIDER range and checks the item's
CURRENT updatedAt. If it now falls outside the original window, our stored
dispensed_at is stale — the item is real and still in Supabase, but
Vetspire's own date-range report would no longer place it in this window,
which is exactly the shape of gap the reconciliation is finding.
"""
import argparse, json, os, urllib.request
from datetime import date, timedelta

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id quantity returned refunded updatedAt }
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


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}",
            headers={
                "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                "Range": f"{offset}-{offset + page_size - 1}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            chunk = json.loads(r.read())
        out.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--wide-start", default="2026-01-01")
    args = ap.parse_args()

    token = load_token()

    print(f"Fetching Supabase order_item_ids for location={args.location} {args.start}..{args.end}...")
    rows = supa_get_all(
        "dispensed_items",
        f"select=order_item_id,dispensed_at,quantity,pulled_at&location_id=eq.{args.location}"
        f"&dispensed_at=gte.{args.start}&dispensed_at=lte.{args.end}T23:59:59",
    )
    supa_ids = {r["order_item_id"]: r for r in rows if r.get("order_item_id")}
    print(f"  {len(supa_ids)} order_item_ids stored in this window\n")

    wide_end = date.today().isoformat()
    print(f"Fetching Vetspire's CURRENT view over a wide range {args.wide_start}..{wide_end}...")
    result = gql(token, USAGE_QUERY, {"lids": [args.location], "s": args.wide_start, "e": wide_end})
    if "errors" in result:
        print(f"ERROR: {result['errors']}"); return
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    vet_by_id = {str(it.get("id")): it for it in order_items}
    print(f"  {len(vet_by_id)} distinct order items found in wide range\n")

    stale = 0
    still_current = 0
    not_found_at_all = 0
    not_found_qty = 0.0
    for oid, row in supa_ids.items():
        vit = vet_by_id.get(oid)
        if not vit:
            not_found_at_all += 1
            qty = float(row.get("quantity") or 0)
            not_found_qty += qty
            print(f"  NOT_FOUND  order_item_id={oid}  stored_dispensed_at={row.get('dispensed_at')}  "
                  f"pulled_at={row.get('pulled_at')}  qty={qty}")
            continue
        current_updated = (vit.get("updatedAt") or "")[:10]
        if args.start <= current_updated <= args.end:
            still_current += 1
        else:
            stale += 1
            print(f"  STALE  order_item_id={oid}  stored_dispensed_at={row.get('dispensed_at')[:10]}  "
                  f"current_vetspire_updatedAt={current_updated}  returned={vit.get('returned')} "
                  f"refunded={vit.get('refunded')}  qty={row.get('quantity')}")

    print(f"\n=== Summary ===")
    print(f"  Still current (updatedAt still in window): {still_current}")
    print(f"  STALE (updatedAt has moved outside window): {stale}")
    print(f"  Not found at all in wide-range query:       {not_found_at_all}  (total qty: {not_found_qty})")


if __name__ == "__main__":
    main()
