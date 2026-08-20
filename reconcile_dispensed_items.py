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

Vetspire's usageReport also returns non-inventory line items (exam fees,
consult charges, etc.) that have no productId/product record at all — they
were never real dispensed products and dispensed_items writers correctly
never capture them (see backfill_date_range.py's skip-if-no-product-id
logic). vetspire_total() below excludes them the same way, otherwise this
check would permanently report a false ~3-4% variance and train everyone to
ignore its red X — which defeats the entire point of a continuous safety
net.

Vetspire's own startDate/endDate windowing on usageReport is unreliable —
confirmed via row-by-row cross-check (Aug 2026 Wheaton incident): an order
item whose updatedAt falls squarely inside a requested window was silently
missing from that window's result set, while a direct/wide-range query for
the same item returned it correctly every time, and the same windowed query
has been observed returning different totals seconds apart. Trusting that
call's own date filter turns this safety net into a false-alarm generator —
the same ~70-unit Wheaton variance flipped sign (Vetspire over then under
Supabase) on back-to-back scheduled runs with no real data change. So
vetspire_total() never asks Vetspire to filter by date: it fetches a wide,
generously-padded range and filters by updatedAt on our side, matching the
method that has matched Supabase exactly in every diagnostic this session.

Usage:
  VETSPIRE_API_TOKEN="..." python3 reconcile_dispensed_items.py [--days 14] [--tolerance-pct 0.5]
"""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PRACTICE_TZ = ZoneInfo("America/Chicago")  # never use bare date.today() — GitHub Actions runners are UTC,
                                            # and usageReport buckets by the practice's local calendar day

WIDE_LOOKBACK_DAYS = 180  # padding before `start` so the wide query safely covers the trailing window

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
        orderItems { id productId product { id } quantity returned refunded updatedAt }
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


def vetspire_total(token, loc_id, start, end):
    wide_start = (datetime.strptime(start, "%Y-%m-%d").date() - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": wide_start, "e": end})
    if "errors" in result:
        raise RuntimeError(result["errors"][0]["message"][:200])
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    by_id = {str(it.get("id")): it for it in items}  # dedupe — the wide range can otherwise double-count
    total = 0.0
    for it in by_id.values():
        if it.get("returned") or it.get("refunded"):
            continue
        if not (it.get("productId") or (it.get("product") or {}).get("id")):
            continue
        updated = (it.get("updatedAt") or "")[:10]
        if not (start <= updated <= end):
            continue
        total += float(it.get("quantity") or 0)
    return total


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
    end = datetime.now(PRACTICE_TZ).date()
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
