#!/usr/bin/env python3
"""
check_today_revenue.py
One-off check: does v_financial_kpis_daily have ANY rows for today's date
yet? User reported Revenue by Source / Revenue per Veterinarian rendering
completely empty with "Today" selected -- this determines whether that's a
real sync gap or Vetspire's salesReport simply not having reported today's
(still-open) business day yet, which no sync frequency could fix.

Report-only. No Supabase writes. Delete once its purpose is served, per
this repo's convention for one-off diagnostics.

Usage:
  python3 check_today_revenue.py
"""
import json, urllib.request
from datetime import date, timedelta

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    day_before = (date.today() - timedelta(days=2)).isoformat()
    print(f"UTC date on this runner: {today}\n")

    for d in [day_before, yesterday, today]:
        rows = get(
            "v_financial_kpis_daily",
            f"select=service_date,location_id,revenue&service_date=eq.{d}",
        )
        total = sum(float(r.get("revenue") or 0) for r in rows)
        print(f"v_financial_kpis_daily {d}: {len(rows)} rows, total revenue ${total:,.2f}")
        for r in rows:
            print(f"    {r}")

    print()
    for d in [day_before, yesterday, today]:
        rows = get(
            "invoice_line_items",
            f"select=service_date,location_id,provider_id,product_category_id,amount&service_date=eq.{d}&limit=5",
        )
        print(f"invoice_line_items {d} (raw, first 5): {rows}")

    # Also check whether scoutsync_financial_unattributed_provider.sql's
    # sentinel provider row has actually been run -- if not, invoice_line_items
    # may be silently duplicating revenue for unattributed transactions on
    # every 4-hour re-sync (NULL provider_id never matches NULL in the
    # ON CONFLICT unique key).
    print()
    sentinel = get("providers", "select=id,vetspire_provider_id,full_name&vetspire_provider_id=eq.__unattributed__")
    print(f"Unattributed-provider sentinel row present: {bool(sentinel)} -- {sentinel}")
    null_provider_rows = get(
        "invoice_line_items",
        f"select=service_date,location_id,amount&provider_id=is.null&service_date=gte.{day_before}",
    )
    total_null_provider = sum(float(r.get("amount") or 0) for r in null_provider_rows)
    print(f"invoice_line_items rows with provider_id=null since {day_before}: "
          f"{len(null_provider_rows)}, total amount ${total_null_provider:,.2f}")


if __name__ == "__main__":
    main()
