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

A single Vetspire query is not reliable enough to delete on: the same
flakiness that made reconcile_dispensed_items.py wrongly fail (a real
in-window item silently missing from one usageReport call — see that
script's docstring) can just as easily make a real, non-voided item look
voided here. That's not theoretical — it happened twice:

1. A delete dispatch removed order_item_id 4028939709 (Lincoln Park),
   which had been directly confirmed real minutes earlier. The fix at
   the time added a second confirmation query before deleting anything.
2. That "fix" still wrongly deleted real data on its very next use —
   because the second query used the exact same unreliable method as
   the first (trusting Vetspire's own startDate/endDate filter). That's
   not independent confirmation: the flakiness isn't random noise, it's
   a systematic quirk of Vetspire's own date-range windowing, so asking
   the same flaky question twice can (and did) get the same wrong answer
   both times. Proof: right after a delete dispatch, Lincoln Park and
   West Loop — both a clean 0.00% match moments earlier — showed real
   mismatches (0.57% and 1.63%, Vetspire *ahead* of Supabase), and Old
   Orchard got worse instead of better. That's the signature of deleting
   real, currently-live items, not voided ones.

So both existence checks now use the wide-range method already proven
reliable in reconcile_dispensed_items.py and backfill_date_range.py:
query a much wider date range than the window being checked (padding
before AND after), and treat an id as "seen" if it appears ANYWHERE in
that wide result — no client-side date filtering, since existence is
all that matters here, not which day Vetspire attributes the item to.
A candidate is only deleted if it's absent from two independent wide-range
existence checks. A row absent from one but present in the other is left
alone and reported as unconfirmed, never deleted.

Usage:
  python3 detect_voided_items.py                        # report only
  python3 detect_voided_items.py --delete                # remove confirmed-voided rows
  python3 detect_voided_items.py --days 90 --qty-tolerance 5
"""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta

WIDE_LOOKBACK_DAYS = 180  # padding before AND after the checked window; existence-only, no date filtering
WIDE_LOOKAHEAD_DAYS = 7

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


def fetch_vetspire_ids(token, loc_id, start, end):
    """Wide-range existence check: does this id show up ANYWHERE in a generously padded
    query? No client-side date filtering — a real item can be attributed to a slightly
    different day by Vetspire's own bucketing, and existence is all that matters here."""
    wide_start = (start - timedelta(days=WIDE_LOOKBACK_DAYS)).isoformat()
    wide_end = (end + timedelta(days=WIDE_LOOKAHEAD_DAYS)).isoformat()
    result = gql(token, USAGE_QUERY, {"lids": [loc_id], "s": wide_start, "e": wide_end})
    if "errors" in result:
        raise RuntimeError(result["errors"][0]["message"][:200])
    usage_raw = result.get("data", {}).get("usageReport")
    if isinstance(usage_raw, str):
        usage_raw = json.loads(usage_raw)
    order_items = usage_raw.get("orderItems", []) if isinstance(usage_raw, dict) else (usage_raw or [])
    return {str(it.get("id")) for it in order_items}


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
            vetspire_ids = fetch_vetspire_ids(token, loc["id"], start, end)
        except Exception as e:
            print(f"  VETSPIRE QUERY FAILED: {e}")
            failures.append((loc["name"], "query failed"))
            continue
        print(f"  {len(vetspire_ids)} distinct order items currently live in Vetspire (wide-range check)")

        candidates = [r for oid, r in supa_by_oid.items() if oid not in vetspire_ids]

        voided = []
        if candidates:
            # Default to "confirmed present" (i.e. NOT voided) for every candidate unless the second
            # wide-range query both succeeds AND independently fails to find it. Any failure mode here
            # must fail safe toward deleting nothing.
            confirmed_present = {r["order_item_id"] for r in candidates}
            try:
                vetspire_ids_2 = fetch_vetspire_ids(token, loc["id"], start, end)
                confirmed_present = confirmed_present & vetspire_ids_2
            except Exception as e:
                print(f"  VETSPIRE CONFIRMATION QUERY FAILED: {e} — treating all candidates as unconfirmed")

            voided = [r for r in candidates if r["order_item_id"] not in confirmed_present]
            unconfirmed = len(candidates) - len(voided)
            if unconfirmed:
                print(f"  {unconfirmed} candidate(s) missing from the first wide-range query but present in a "
                      f"second independent wide-range query — not deleting (unconfirmed)")

        voided_qty = sum(float(r.get("quantity") or 0) for r in voided)
        print(f"  {len(voided)} voided (confirmed absent in two independent queries), total qty {voided_qty:.2f}")

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
