#!/usr/bin/env python3
"""
vetspire_financial_reconciliation_check.py
Read-only check: pulls fresh totals straight from Vetspire's salesReport for
a window of fully-elapsed days and compares them against what's actually
sitting in Supabase's invoice_line_items for the exact same window — to
confirm the Financial tab's numbers genuinely mirror Vetspire, not just that
the sync ran without errors.

Two checks per location:
  1. Total revenue — a no-breakdown salesReport call (the simplest possible
     authoritative number) vs. sum(amount) in invoice_line_items.
  2. Revenue by category — a PRODUCT_CATEGORY_ID-breakdown salesReport call
     vs. invoice_line_items grouped by product_category_id, so the "Revenue
     by Source" tiles are checked too, not just the headline total.

Excludes today (still-accumulating, would look like a false mismatch) —
only reconciles days that have fully elapsed.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_financial_reconciliation_check.py
  RECONCILE_DAYS=14 VETSPIRE_API_TOKEN="..." python3 vetspire_financial_reconciliation_check.py
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

LOCATIONS = {
    "23083": ("11111111-0000-0000-0000-000000000001", "Lincoln Park"),
    "27390": ("11111111-0000-0000-0000-000000000002", "Old Orchard"),
    "24356": ("11111111-0000-0000-0000-000000000003", "West Loop"),
    "28253": ("11111111-0000-0000-0000-000000000004", "Wheaton"),
}

RECONCILE_DAYS = int(os.environ.get("RECONCILE_DAYS", "7"))
MISMATCH_THRESHOLD_PCT = 1.0

TOTAL_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e, segment:DAY)
}
"""

CATEGORY_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                breakdowns:[PRODUCT_CATEGORY_ID], segment:DAY)
}
"""


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,  # permanent API key — no Bearer prefix
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def sales_rows(token, query, loc_id, since, until):
    result = gql(token, query, {"lids": [loc_id], "s": since, "e": until})
    if "errors" in result:
        return None, result["errors"]
    raw = result.get("data", {}).get("salesReport", "[]")
    rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
    return rows, None


def pct_diff(a, b):
    if a == 0 and b == 0:
        return 0.0
    if a == 0:
        return 100.0
    return abs(a - b) / a * 100


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    now = datetime.now(timezone.utc)
    until = (now - timedelta(days=1)).strftime("%Y-%m-%d")           # last fully-elapsed day
    since = (now - timedelta(days=RECONCILE_DAYS)).strftime("%Y-%m-%d")

    print(f"Reconciling {since} through {until} ({RECONCILE_DAYS} fully-elapsed days, today excluded)\n")

    any_mismatch = False
    overall_vs, overall_supa = 0.0, 0.0

    for vs_loc_id, (loc_uuid, loc_name) in LOCATIONS.items():
        print(f"=== {loc_name} ===")

        # ── 1. Headline total ──
        rows, err = sales_rows(token, TOTAL_QUERY, vs_loc_id, since, until)
        if err:
            print(f"  ERROR fetching Vetspire total: {err}")
            any_mismatch = True
            continue
        vs_total = sum(float(r.get("total") or 0) for r in rows)

        supa_rows = supa_get(
            "invoice_line_items",
            f"select=amount&location_id=eq.{loc_uuid}&service_date=gte.{since}&service_date=lte.{until}",
        )
        supa_total = sum(float(r.get("amount") or 0) for r in supa_rows)

        diff_pct = pct_diff(vs_total, supa_total)
        status = "OK" if diff_pct <= MISMATCH_THRESHOLD_PCT else "MISMATCH"
        if status == "MISMATCH":
            any_mismatch = True
        print(f"  Total revenue — Vetspire: ${vs_total:,.2f}  Supabase: ${supa_total:,.2f}  diff: {diff_pct:.1f}%  [{status}]")
        overall_vs += vs_total
        overall_supa += supa_total

        # ── 2. Category breakdown ──
        cat_rows, err = sales_rows(token, CATEGORY_QUERY, vs_loc_id, since, until)
        if err:
            print(f"  ERROR fetching Vetspire category breakdown: {err}")
            any_mismatch = True
            continue
        vs_by_cat = {}
        for r in cat_rows:
            cat = r.get("product_category_id") or 0
            vs_by_cat[cat] = vs_by_cat.get(cat, 0) + float(r.get("total") or 0)

        supa_cat_rows = supa_get(
            "invoice_line_items",
            f"select=product_category_id,amount&location_id=eq.{loc_uuid}&service_date=gte.{since}&service_date=lte.{until}",
        )
        supa_by_cat = {}
        for r in supa_cat_rows:
            cat = r.get("product_category_id") or 0
            supa_by_cat[cat] = supa_by_cat.get(cat, 0) + float(r.get("amount") or 0)

        all_cats = sorted(set(vs_by_cat) | set(supa_by_cat))
        cat_mismatches = 0
        for cat in all_cats:
            a, b = vs_by_cat.get(cat, 0), supa_by_cat.get(cat, 0)
            if pct_diff(a, b) > MISMATCH_THRESHOLD_PCT:
                cat_mismatches += 1
                print(f"    category {cat}: Vetspire ${a:,.2f} vs Supabase ${b:,.2f} — MISMATCH")
        if cat_mismatches:
            any_mismatch = True
            print(f"  category breakdown: {cat_mismatches}/{len(all_cats)} categories mismatched")
        else:
            print(f"  category breakdown: all {len(all_cats)} categories match")
        print()

    print(f"=== TOTAL — Vetspire: ${overall_vs:,.2f}  Supabase: ${overall_supa:,.2f} ===")
    if any_mismatch:
        print("\n*** One or more checks above show a mismatch beyond "
              f"{MISMATCH_THRESHOLD_PCT}% — investigate before trusting the Financial tab. ***")
        sys.exit(1)
    print("\nAll locations and categories match within "
          f"{MISMATCH_THRESHOLD_PCT}% — Financial tab numbers mirror Vetspire.")


if __name__ == "__main__":
    main()
