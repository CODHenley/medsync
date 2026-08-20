#!/usr/bin/env python3
"""
diagnose_chem17_mismatch.py
Read-only, one-off. MedSync's Procurement screen showed 131 units dispensed
for Catalyst Chem 17 (SKU 98-11003-02) across all 4 locations for
2026-08-01..2026-08-20, while Vetspire's own Usage Report for the identical
range/locations showed 130. Checks, per location:
  - exact count + sum of Supabase dispensed_items rows for this SKU/range
  - whether any order_item_id appears more than once (a real duplicate-row
    double-count, not just a query artifact)
  - a fresh Vetspire wide-range query, cross-checked row-by-row against every
    stored order_item_id, to find any item Supabase has that Vetspire
    doesn't currently agree with (voided, quantity-changed, or genuinely
    absent)
"""
import json, os, urllib.request
from collections import Counter
from datetime import date

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

SKU = "98-11003-02"
START = "2026-08-01"
END   = "2026-08-20"
WIDE_START = "2026-01-01"

LOCATIONS = [
    {"id": "23083", "name": "Lincoln Park"},
    {"id": "27390", "name": "Old Orchard"},
    {"id": "24356", "name": "West Loop"},
    {"id": "28253", "name": "Wheaton"},
]

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id productId product { id sku } quantity returned refunded updatedAt }
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
            f"{SUPA_URL}/rest/v1/{path}?{params}&order=id",
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
    token = load_token()
    wide_end = date.today().isoformat()

    grand_supa_total = 0.0
    grand_vet_total = 0.0

    for loc in LOCATIONS:
        print(f"\n=== {loc['name']} ===")
        rows = supa_get_all(
            "dispensed_items",
            f"select=id,order_item_id,quantity,returned,refunded,dispensed_at,vetspire_product_id"
            f"&location_id=eq.{loc['id']}&sku=eq.{SKU}"
            f"&dispensed_at=gte.{START}&dispensed_at=lte.{END}T23:59:59",
        )
        active_rows = [r for r in rows if not r.get("returned") and not r.get("refunded")]
        supa_qty = sum(float(r.get("quantity") or 0) for r in active_rows)
        grand_supa_total += supa_qty
        print(f"  Supabase: {len(rows)} rows total ({len(active_rows)} active), qty={supa_qty}")

        # Duplicate order_item_id check — a real double-write, not a query artifact
        oid_counts = Counter(r.get("order_item_id") for r in rows if r.get("order_item_id"))
        dupes = {oid: c for oid, c in oid_counts.items() if c > 1}
        if dupes:
            print(f"  DUPLICATE order_item_id(s) stored more than once: {dupes}")
            for oid in dupes:
                for r in rows:
                    if r.get("order_item_id") == oid:
                        print(f"    row id={r['id']} order_item_id={oid} qty={r.get('quantity')} "
                              f"dispensed_at={r.get('dispensed_at')} returned={r.get('returned')} refunded={r.get('refunded')}")
        else:
            print("  No duplicate order_item_id rows.")

        # Fresh Vetspire wide-range pull for this location
        result = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": WIDE_START, "e": wide_end})
        if "errors" in result:
            print(f"  VETSPIRE ERROR: {result['errors']}")
            continue
        usage_raw = result.get("data", {}).get("usageReport")
        if isinstance(usage_raw, str):
            usage_raw = json.loads(usage_raw)
        order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
        vet_by_id = {str(it.get("id")): it for it in order_items}

        vet_qty_for_stored = 0.0
        print("  Row-by-row vs fresh Vetspire pull:")
        for r in active_rows:
            oid = r.get("order_item_id")
            vit = vet_by_id.get(oid)
            if not vit:
                print(f"    order_item_id={oid} qty={r.get('quantity')} dispensed_at={r.get('dispensed_at')} "
                      f"=> NOT FOUND in fresh Vetspire pull (voided or query gap)")
                continue
            v_sku = (vit.get("product") or {}).get("sku")
            v_qty = float(vit.get("quantity") or 0)
            v_ret = vit.get("returned") or vit.get("refunded")
            if v_sku != SKU or v_ret:
                print(f"    order_item_id={oid} stored_qty={r.get('quantity')} "
                      f"=> vetspire_sku={v_sku} vetspire_qty={v_qty} vetspire_returned/refunded={v_ret} MISMATCH")
                continue
            if abs(v_qty - float(r.get("quantity") or 0)) > 0.001:
                print(f"    order_item_id={oid} stored_qty={r.get('quantity')} vetspire_qty={v_qty}  QTY MISMATCH")
            vet_qty_for_stored += v_qty

        # Vetspire items in this SKU/date range that Supabase never captured at all
        wide_stored_ids = {r.get("order_item_id") for r in rows if r.get("order_item_id")}
        missing_from_supa = []
        for it in order_items:
            sku = (it.get("product") or {}).get("sku")
            if sku != SKU:
                continue
            if it.get("returned") or it.get("refunded"):
                continue
            updated = (it.get("updatedAt") or "")[:10]
            if not (START <= updated <= END):
                continue
            if str(it.get("id")) not in wide_stored_ids:
                missing_from_supa.append(it)
        if missing_from_supa:
            print(f"  Vetspire item(s) in range NOT captured in Supabase at all:")
            for it in missing_from_supa:
                print(f"    order_item_id={it.get('id')} qty={it.get('quantity')} updatedAt={it.get('updatedAt')}")

        print(f"  Vetspire qty (matching Supabase's stored order_item_ids): {vet_qty_for_stored}")
        grand_vet_total += vet_qty_for_stored

    print(f"\n=== TOTALS ===")
    print(f"  Supabase active qty summed across 4 locations: {grand_supa_total}")
    print(f"  Vetspire qty for those same order_item_ids:    {grand_vet_total}")


if __name__ == "__main__":
    main()
