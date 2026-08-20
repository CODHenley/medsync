#!/usr/bin/env python3
"""
verify_full_backfill.py
Read-only. Confirms the full-history per-item backfill (order_item_id
populated) alone already matches Vetspire's real totals, BEFORE any legacy
(order_item_id IS NULL) row is deleted. Queries Vetspire in the same
quarterly chunks the backfill used, per location, to avoid huge single
responses, and compares against Supabase's order_item_id-populated rows
only (excludes legacy rows entirely, so this proves the new data is
complete on its own — not merely "total including legacy" matching, which
would hide a legacy row masking a still-incomplete per-item backfill).
"""
import json, os, sys, urllib.request

VETSPIRE_URL    = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"
SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = [
    {"id": "23083", "name": "Lincoln Park"},
    {"id": "27390", "name": "Old Orchard"},
    {"id": "24356", "name": "West Loop"},
    {"id": "28253", "name": "Wheaton"},
]

WINDOWS = [
    ("2024-11-01", "2025-02-28"),
    ("2025-03-01", "2025-05-31"),
    ("2025-06-01", "2025-08-31"),
    ("2025-09-01", "2025-11-30"),
    ("2025-12-01", "2026-02-28"),
    ("2026-03-01", "2026-05-31"),
    ("2026-06-01", "2026-08-18"),
]

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { productId product { id } quantity returned refunded }
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


def vetspire_total(token, loc_id, start, end):
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": start, "e": end})
    if "errors" in result:
        raise RuntimeError(result["errors"][0]["message"][:200])
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    # Exclude non-inventory line items (exam fees, consult charges) that have
    # no productId/product record — dispensed_items writers never capture
    # these (see backfill_date_range.py), so including them here would
    # compare against a baseline the backfill was never meant to match.
    return sum(float(it.get("quantity") or 0) for it in items
               if not it.get("returned") and not it.get("refunded")
               and (it.get("productId") or (it.get("product") or {}).get("id")))


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


def supabase_populated_total(loc_id, start, end):
    rows = supa_get_all(
        "dispensed_items",
        f"select=quantity,returned,refunded&location_id=eq.{loc_id}"
        f"&order_item_id=not.is.null"
        f"&dispensed_at=gte.{start}&dispensed_at=lte.{end}T23:59:59",
    )
    return sum(float(r.get("quantity") or 0) for r in rows
               if not r.get("returned") and not r.get("refunded"))


def main():
    token = load_token()
    failures = []
    for loc in LOCATIONS:
        vet_total = 0.0
        supa_total = 0.0
        for start, end in WINDOWS:
            try:
                vet_total += vetspire_total(token, loc["id"], start, end)
            except Exception as e:
                print(f"  [{loc['name']}] {start}..{end} VETSPIRE QUERY FAILED: {e}")
                failures.append((loc["name"], start, end, "query failed"))
                continue
            supa_total += supabase_populated_total(loc["id"], start, end)
        diff = vet_total - supa_total
        pct = (abs(diff) / vet_total * 100) if vet_total else (100.0 if supa_total else 0.0)
        status = "OK" if pct <= 0.1 else "MISMATCH"
        print(f"[{loc['name']:12s}] vetspire={vet_total:10.1f}  supabase(populated only)={supa_total:10.1f}  "
              f"diff={diff:+9.1f}  ({pct:5.2f}%)  {status}")
        if pct > 0.1:
            failures.append((loc["name"], None, None, f"{pct:.2f}% variance"))

    print()
    if failures:
        print(f"=== FAIL: {len(failures)} location(s)/window(s) out of tolerance — full backfill NOT yet complete ===")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("=== PASS: order_item_id-populated rows alone match Vetspire at every location — safe to delete legacy rows ===")


if __name__ == "__main__":
    main()
