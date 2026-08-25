#!/usr/bin/env python3
"""
vetspire_financial_sync.py
Syncs Vetspire's salesReport (day-level, broken down by provider + product
category) into ScoutSync's invoice_line_items table — backs Revenue by
Source and Revenue per Veterinarian. Average Cost per Transaction (ACT) is
computed in the view layer as revenue ÷ encounter count for the same day/location,
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
import json, os, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s between attempts


def _urlopen_with_retry(req, timeout):
    """Retries transient failures (5xx, connection resets, timeouts) with backoff.
    4xx errors are raised immediately -- retrying a bad request won't help.
    Without this, a single Supabase HTTP 500 or a dropped TLS connection killed
    the whole run outright instead of costing a few seconds."""
    last_err = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"    transient error ({last_err}) — retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            time.sleep(wait)
    raise last_err

LOCATIONS = {
    "23083": ("11111111-0000-0000-0000-000000000001", "Lincoln Park"),
    "27390": ("11111111-0000-0000-0000-000000000002", "Old Orchard"),
    "24356": ("11111111-0000-0000-0000-000000000003", "West Loop"),
    "28253": ("11111111-0000-0000-0000-000000000004", "Wheaton"),
}

LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "3"))
# Default 3 = overlap window so a missed scheduled run gets caught by the next
# one. Override via the LOOKBACK_DAYS env var (or the workflow_dispatch input)
# for a one-time historical backfill — e.g. 30 to match daily_revenue's
# existing trailing-30-day history so the reconciliation check has something
# real to compare against instead of ~3/30 of it.

SALES_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                breakdowns:[PROVIDER_ID, PRODUCT_CATEGORY_ID], segment:DAY)
}
"""

# Small, practice-wide reference list (18 categories, confirmed via
# vetspire_clinical_schema_probe.py) — real names like "IDEXX In-house" and
# "Vaccines - Canine" instead of invoice_line_items' raw numeric
# product_category_id. Synced every run so a rename in Vetspire is picked up.
CATEGORIES_QUERY = "{ productCategories { id name } }"


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,  # permanent API key — no Bearer prefix
    })
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}&order=id",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    body, _ = _urlopen_with_retry(req, timeout=20)
    return json.loads(body)


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
        body, _ = _urlopen_with_retry(req, timeout=20)
        return json.loads(body)
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
    # this sync hasn't seen yet falls back to the fixed UNATTRIBUTED_PROVIDER
    # sentinel below (still counted, just not resolved to a specific vet) —
    # never to None/null. Postgres treats NULL != NULL in a unique constraint,
    # so a null provider_id would never match on ON CONFLICT and every re-run
    # would insert a fresh duplicate row instead of updating the existing one,
    # silently multiplying revenue over time. See
    # scoutsync_financial_unattributed_provider.sql for the sentinel row.
    UNATTRIBUTED_PROVIDER = "00000000-0000-0000-0000-000000000000"
    provider_uuid_by_vs = {
        p["vetspire_provider_id"]: p["id"]
        for p in supa_get("providers", "select=id,vetspire_provider_id")
    }

    cat_result = gql(token, CATEGORIES_QUERY)
    if "errors" in cat_result:
        print(f"  WARNING: productCategories fetch failed: {cat_result['errors']}")
    else:
        categories = cat_result.get("data", {}).get("productCategories") or []
        cat_rows = [{"id": int(c["id"]), "name": c["name"]} for c in categories if c.get("id")]
        supa_upsert("product_categories", cat_rows, "id")
        print(f"  synced {len(cat_rows)} product categories")

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
            provider_uuid = provider_uuid_by_vs.get(str(provider_vs_id)) if provider_vs_id else None
            line_items.append({
                "location_id": loc_uuid,
                "provider_id": provider_uuid or UNATTRIBUTED_PROVIDER,
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
