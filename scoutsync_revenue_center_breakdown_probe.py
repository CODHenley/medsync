#!/usr/bin/env python3
"""
scoutsync_revenue_center_breakdown_probe.py
Before extending vetspire_financial_sync.py to also capture revenue_center_id
(so the dashboard can label the "Uncategorized" bucket by real revenue
center -- Radiographs/Inhouse laboratory/Treatments -- instead of lumping
it), confirm whether salesReport actually accepts a 3-way breakdown
(PROVIDER_ID + PRODUCT_CATEGORY_ID + REVENUE_CENTER_ID together), since
every confirmed prior use of this API was only ever a 2-way breakdown.

Report-only. No writes. Delete once its purpose is served, per this
repo's convention for one-off diagnostics.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_revenue_center_breakdown_probe.py
"""
import json, os, urllib.request, urllib.error
from datetime import date, timedelta

VETSPIRE_URL = "https://api.vetspire.com/graphql"


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": token,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:500]}"}]}


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip().removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    end = date.today()
    start = end - timedelta(days=90)

    print("=== 3-way breakdown: PROVIDER_ID + PRODUCT_CATEGORY_ID + REVENUE_CENTER_ID ===")
    query = """
    query($lids:[ID!], $s:Date, $e:Date){
        salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                    breakdowns:[PROVIDER_ID, PRODUCT_CATEGORY_ID, REVENUE_CENTER_ID], segment:DAY)
    }
    """
    r = gql(token, query, {"lids": ["28253"], "s": start.isoformat(), "e": end.isoformat()})
    if "errors" in r:
        print(f"  ERROR: {r['errors']}")
    else:
        raw = r.get("data", {}).get("salesReport", "[]")
        rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
        print(f"  {len(rows)} rows over {start}..{end} (Wheaton)")
        uncategorized = [row for row in rows if row.get("product_category_id") in (None, 0)]
        print(f"  {len(uncategorized)} of those rows are uncategorized (product_category_id null/0) -- "
              f"does revenue_center_id populate for THESE specifically?")
        for row in uncategorized[:15]:
            print(f"  - {row}")
        if not uncategorized:
            print("  (none in this 7-day window -- showing first 10 of all rows instead)")
            for row in rows[:10]:
                print(f"  - {row}")
    print()

    print("=== Root query fields matching 'revenueCenters' (for a full reference list) ===")
    r = gql(token, "{ revenueCenters { id name } }")
    if "errors" in r:
        print(f"  ERROR: {r['errors']}")
    else:
        cats = (r.get("data") or {}).get("revenueCenters") or []
        print(f"  {len(cats)} revenue centers")
        for c in cats:
            print(f"    {c}")


if __name__ == "__main__":
    main()
