#!/usr/bin/env python3
"""
vetspire_financial_sync.py
Syncs Vetspire's salesReport (day-level, broken down by provider + product
category) into ScoutSync's invoice_line_items table — backs Revenue by
Source and Revenue per Veterinarian. Average Transaction Charge is computed
in the view layer as revenue ÷ encounter count for the same day/location,
since salesReport returns pre-aggregated totals, not individual invoices —
there's no invoice count to divide by directly.

Field names and arguments confirmed via vetspire_clinical_schema_probe.py
against the production schema:
  - salesReport(locationIds, startDate, endDate, breakdowns: [ReportBreakdown!], segment: ReportSegment)
  - segment=DAY gives real daily rows (confirmed: matched Wheaton's actual
    Aug 16 total, $3,459.30, exactly)
  - row shape: {"total": "<decimal string>", "date": "YYYY-MM-DD",
    "provider_id": <int>, "product_category_id": <int or null>}

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_financial_sync.py
"""
import json, os, urllib.request, urllib.error
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

LOOKBACK_DAYS = 3  # overlap window so a missed run gets caught by the next one

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                breakdowns:[PROVIDER_ID, PRODUCT_CATEGORY_ID], segment:DAY)
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


def supa_upsert(path, records, on_conflict):
    if not records:
        return []
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?on_conflict={on_conflict}",
        data=body, method="POST",
        headers={
            "Content-Type":  "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "resolution=merge-duplicates,return=representation",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code} on {path}: {e.read().decode()[:300]}")
        return []


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip()
    token = token.removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    # Providers are synced independently by vetspire_clinical_sync.py — look
    # up existing ones rather than re-syncing the roster here. A provider_id
    # this sync hasn't seen yet just lands as unattributed revenue (still
    # counted, just not resolved to a specific vet).
    provider_uuid_by_vs = {
        p["vetspire_provider_id"]: p["id"]
        for p in supa_get("providers", "select=id,vetspire_provider_id")
    }

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    until = now.strftime("%Y-%m-%d")

    total_rows = 0
    for vetspire_loc_id, (loc_uuid, loc_name) in LOCATIONS.items():
        print(f"\n=== {loc_name} ({vetspire_loc_id}) ===")
        result = gql(token, SALES_QUERY, {
            "lids": [vetspire_loc_id], "s": since, "e": until,
        })
        if "errors" in result:
            print(f"  ERROR: {result['errors']}")
            continue
        raw = result.get("data", {}).get("salesReport", "[]")
        rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
        print(f"  fetched {len(rows)} breakdown rows")

        line_items = []
        for row in rows:
            provider_vs_id = row.get("provider_id")
            line_items.append({
                "location_id": loc_uuid,
                "provider_id": provider_uuid_by_vs.get(str(provider_vs_id)) if provider_vs_id else None,
                "product_category_id": row.get("product_category_id") or 0,
                "amount": float(row.get("total") or 0),
                "service_date": row.get("date"),
            })

        out = supa_upsert(
            "invoice_line_items", line_items,
            "location_id,provider_id,product_category_id,service_date",
        )
        print(f"  upserted {len(out)} rows")
        total_rows += len(out)

    print(f"\n=== Done — {total_rows} invoice_line_items rows upserted ===")


if __name__ == "__main__":
    main()
