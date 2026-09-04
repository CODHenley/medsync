#!/usr/bin/env python3
"""
scoutsync_round3_live_verify.py
Round 3, ground truth pass: we just proved "Exam - Urgent Care" is
CORRECTLY categorized in Vetspire (round 1 fix holds) despite still
showing up as the #1 uncategorized item in Supabase's dispensed_items --
a full-history backfill re-run didn't fix it either, pointing to
usageReport silently truncating large monthly result sets for
high-volume products rather than a category-write problem.

Before proposing round 3 category recommendations, get the REAL current
Vetspire category for every distinct product behind the top 80
uncategorized names, via a direct product(id) query (the same one used
for every write-verification in this project) -- not by trusting
Supabase's cached state. This tells us definitively which names are
pipeline artifacts (already correctly categorized -- exclude from any
proposal) vs genuinely still uncategorized in Vetspire (real candidates
for round 3).

Read-only. Deleted once its purpose is served, per this repo's
convention.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from collections import defaultdict

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

VETSPIRE_URL = "https://api.vetspire.com/graphql"
VETSPIRE_ORIGIN = "https://scoutcare.vetspire.com"

TOP_N_NAMES = 80


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set.")
    return token.removeprefix("Bearer ").strip()


def supa_get(path, params):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{params}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        page = supa_get(path, f"{params}&limit={page_size}&offset={offset}")
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": token,
            "Origin": VETSPIRE_ORIGIN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:300]}"}]}


def main():
    token = load_token()

    print("=== Round 3 ground truth: live Vetspire category per top-80 uncategorized name ===\n")

    rows = supa_get_all(
        "dispensed_items",
        "select=product_name,vetspire_product_id,subtotal_cents&product_category_id=is.null",
    )
    by_name = defaultdict(lambda: {"count": 0, "revenue": 0.0, "product_ids": set()})
    for r in rows:
        name = r.get("product_name") or "(blank)"
        s = by_name[name]
        s["count"] += 1
        s["revenue"] += (r.get("subtotal_cents") or 0) / 100.0
        pid = r.get("vetspire_product_id")
        if pid:
            s["product_ids"].add(str(pid))

    ranked = sorted(by_name.items(), key=lambda kv: kv[1]["revenue"], reverse=True)[:TOP_N_NAMES]

    all_pids = sorted({pid for _, s in ranked for pid in s["product_ids"]})
    print(f"-- {len(ranked)} names, {len(all_pids)} distinct product_ids to check live --\n")

    pid_to_live_category = {}
    for i, pid in enumerate(all_pids):
        result = gql(token, "query($id: ID) { product(id: $id) { id name productCategories { id name } } }", {"id": pid})
        if "errors" in result:
            print(f"  !! error checking product_id={pid}: {result['errors']}")
            pid_to_live_category[pid] = "ERROR"
        else:
            cats = ((result.get("data") or {}).get("product") or {}).get("productCategories") or []
            pid_to_live_category[pid] = cats[0]["name"] if cats else None
        if (i + 1) % 20 == 0:
            print(f"  ...checked {i+1}/{len(all_pids)}")

    print(f"\n-- Results: name -> live Vetspire category per product_id --\n")
    already_fixed = []
    genuinely_uncategorized = []
    mixed = []
    had_error = []

    for name, s in ranked:
        live_cats = {pid: pid_to_live_category.get(pid) for pid in s["product_ids"]}
        distinct_live = set(live_cats.values())
        if "ERROR" in distinct_live:
            had_error.append((name, s, live_cats))
            status = f"COULD NOT VERIFY (API error): {live_cats}"
        elif distinct_live == {None}:
            genuinely_uncategorized.append((name, s))
            status = "STILL UNCATEGORIZED in Vetspire"
        elif None not in distinct_live:
            already_fixed.append((name, s, distinct_live))
            status = f"ALREADY CATEGORIZED in Vetspire: {distinct_live} (pipeline artifact)"
        else:
            mixed.append((name, s, live_cats))
            status = f"MIXED: {live_cats}"
        print(f"  {s['count']:>5}x  ${s['revenue']:>10,.2f}  {name!r}: {status}")

    print(f"\n=== Summary ===")
    print(f"  Genuinely still uncategorized in Vetspire: {len(genuinely_uncategorized)} names")
    print(f"  Already categorized in Vetspire (pipeline artifact, exclude): {len(already_fixed)} names")
    print(f"  Mixed (some product_ids fixed, some not): {len(mixed)} names")
    print(f"  Could not verify (API error): {len(had_error)} names")


if __name__ == "__main__":
    main()
