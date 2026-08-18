#!/usr/bin/env python3
"""
reconcile_dispensed_items.py
Continuous safety net for dispensed_items — runs on a schedule (see
.github/workflows/reconcile_dispensed_items.yml), not just on request.

Compares Vetspire's real usageReport totals against what's stored in
Supabase's dispensed_items for every location over a trailing window, and
EXITS NON-ZERO (failing the workflow, which shows as a red X and is visible
in GitHub) the moment any location's variance exceeds a small tolerance.

This exists because the Aug 2026 double-count/undercount incidents were both
only found because a human happened to ask "why doesn't this add up" — this
makes that check continuous instead of depending on someone noticing.

Usage:
  VETSPIRE_API_TOKEN="..." python3 reconcile_dispensed_items.py [--days 14] [--tolerance-pct 0.5]
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
        orderItems { quantity returned refunded }
    }
}
"""


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if token:
        return token.removeprefix("Bearer ").strip()
    for path in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vetspire_token.txt"),
        os.path.expanduser("~/.vetspire_token"),
    ):
        if os.path.exists(path):
            return open(path).read().strip().removeprefix("Bearer ").strip()
    raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set and no token file found.")


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


def vetspire_total(token, loc_id, start, end):
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": start, "e": end})
    if "errors" in result:
        raise RuntimeError(result["errors"][0]["message"][:200])
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    return sum(float(it.get("quantity") or 0) for it in items
               if not it.get("returned") and not it.get("refunded"))


def supabase_total(loc_id, start, end):
    rows = supa_get_all(
        "dispensed_items",
        f"select=quantity,returned,refunded&location_id=eq.{loc_id}"
        f"&dispensed_at=gte.{start}&dispensed_at=lte.{end}T23:59:59",
    )
    return sum(float(r.get("quantity") or 0) for r in rows
               if not r.get("returned") and not r.get("refunded"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="Trailing window size in days")
    ap.add_argument("--tolerance-pct", type=float, default=0.5, help="Allowed variance %% before failing")
    args = ap.parse_args()

    token = load_token()
    end = date.today()
    start = end - timedelta(days=args.days)
    print(f"\n=== Reconciling dispensed_items: trailing {args.days} days ({start} → {end}) ===")
    print(f"    Excludes today (still-accumulating partial day, not a real variance)\n")
    check_end = end - timedelta(days=1)  # never compare against today's partial data

    failures = []
    for loc in LOCATIONS:
        try:
            vet = vetspire_total(token, loc["id"], start.isoformat(), check_end.isoformat())
        except Exception as e:
            print(f"  [{loc['name']}] VETSPIRE QUERY FAILED: {e}")
            failures.append((loc["name"], None, None, "query failed"))
            continue
        supa = supabase_total(loc["id"], start.isoformat(), check_end.isoformat())
        diff = vet - supa
        pct = (abs(diff) / vet * 100) if vet else (100.0 if supa else 0.0)
        status = "OK" if pct <= args.tolerance_pct else "MISMATCH"
        print(f"  [{loc['name']:12s}] Vetspire={vet:9.1f}  Supabase={supa:9.1f}  diff={diff:+8.1f}  ({pct:5.2f}%)  {status}")
        if pct > args.tolerance_pct:
            failures.append((loc["name"], vet, supa, f"{pct:.2f}% variance"))

    print()
    if failures:
        print(f"=== FAIL: {len(failures)} location(s) out of tolerance ===")
        for name, vet, supa, reason in failures:
            print(f"  {name}: {reason}" + (f" (Vetspire {vet}, Supabase {supa})" if vet is not None else ""))
        sys.exit(1)
    else:
        print("=== PASS: all locations within tolerance ===")


if __name__ == "__main__":
    main()
