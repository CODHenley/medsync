#!/usr/bin/env python3
"""
detect_voided_items.py
Continuous safety net — companion to reconcile_dispensed_items.py.

Vetspire order items can be voided or deleted after we've already captured
them (e.g. staff correcting a data-entry mistake). Our pipeline only ever
upserts — it never learns that a previously-real item has since been
retracted — so a voided item's row lingers in dispensed_items forever,
silently overstating COGS. Confirmed root cause of the Aug 2026
reconciliation gap: Old Orchard's entire residual mismatch (387 qty across
60 items) and roughly half of Lincoln Park's (142 qty across 39 items)
were voided Vetspire records still sitting in Supabase.

Scans a rolling trailing window of stored order_item_ids against
Vetspire's CURRENT live data. Any stored item no longer present there is
voided. Reports by default; --delete actually removes the confirmed-voided
rows (see .github/workflows/detect_voided_items.yml for both the scheduled
report-only run and the manual delete dispatch).

Usage:
  python3 detect_voided_items.py                        # report only
  python3 detect_voided_items.py --delete                # remove confirmed-voided rows
  python3 detect_voided_items.py --days 90 --qty-tolerance 5
"""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta

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

USAGE_QUERY = """
query($lids:[ID!], $s:Date, $e:Date){
    usageReport(locationIds:$lids, startDate:$s, endDate:$e) {
        orderItems { id }
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


def supa_delete_by_ids(ids):
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        id_list = ",".join(chunk)
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/dispensed_items?id=in.({id_list})",
            headers={
                "apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                "Prefer": "return=minimal",
            },
        )
        req.get_method = lambda: "DELETE"
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"    deleted chunk of {len(chunk)} — HTTP {r.status}")
        except urllib.error.HTTPError as e:
            print(f"    ERROR deleting chunk: {e.code} {e.read().decode()[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="Rolling trailing window in days")
    ap.add_argument("--qty-tolerance", type=float, default=5.0,
                    help="Allowed voided quantity per location before failing")
    ap.add_argument("--delete", action="store_true", help="Actually remove confirmed-voided rows")
    args = ap.parse_args()

    token = load_token()
    end = date.today()
    start = end - timedelta(days=args.days)
    print(f"\n=== Detecting voided Vetspire order items: trailing {args.days} days ({start} → {end}) ===\n")

    failures = []
    total_deleted = 0
    for loc in LOCATIONS:
        print(f"--- {loc['name']} ---")
        rows = supa_get_all(
            "dispensed_items",
            f"select=id,order_item_id,quantity&location_id=eq.{loc['id']}"
            f"&order_item_id=not.is.null"
            f"&dispensed_at=gte.{start.isoformat()}&dispensed_at=lte.{end.isoformat()}T23:59:59",
        )
        supa_by_oid = {r["order_item_id"]: r for r in rows if r.get("order_item_id")}
        print(f"  {len(supa_by_oid)} order_item_ids stored in window")

        try:
            result = gql(token, USAGE_QUERY, {"lids": [loc["id"]], "s": start.isoformat(), "e": end.isoformat()})
        except Exception as e:
            print(f"  VETSPIRE QUERY FAILED: {e}")
            failures.append((loc["name"], "query failed"))
            continue
        if "errors" in result:
            print(f"  VETSPIRE API ERROR: {result['errors'][0]['message'][:200]}")
            failures.append((loc["name"], "API error"))
            continue
        usage_raw = result.get("data", {}).get("usageReport")
        if isinstance(usage_raw, str):
            usage_raw = json.loads(usage_raw)
        order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
        vetspire_ids = {str(it.get("id")) for it in order_items}
        print(f"  {len(vetspire_ids)} distinct order items currently live in Vetspire")

        voided = [r for oid, r in supa_by_oid.items() if oid not in vetspire_ids]
        voided_qty = sum(float(r.get("quantity") or 0) for r in voided)
        print(f"  {len(voided)} voided (no longer exist in Vetspire), total qty {voided_qty:.2f}")

        if voided_qty > args.qty_tolerance:
            failures.append((loc["name"], f"{voided_qty:.2f} qty voided but still stored"))

        if args.delete and voided:
            print(f"  DELETING {len(voided)} voided rows...")
            supa_delete_by_ids([r["id"] for r in voided])
            total_deleted += len(voided)

    print()
    if args.delete:
        print(f"=== Done: {total_deleted} voided rows deleted ===")
    elif failures:
        print(f"=== FAIL: {len(failures)} location(s) have voided items still counted ===")
        for name, reason in failures:
            print(f"  {name}: {reason}")
        sys.exit(1)
    else:
        print("=== PASS: no location has more than tolerance voided quantity still stored ===")


if __name__ == "__main__":
    main()
