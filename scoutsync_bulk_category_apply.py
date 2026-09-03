#!/usr/bin/env python3
"""
scoutsync_bulk_category_apply.py
User-authorized bulk categorization: applies the category recommendations
already reviewed and approved by the user to the real uncategorized
services in Vetspire, using updateProductProductCategory (write access
confirmed working via scoutsync_category_writeback_test.py -- since
removed, its purpose served).

Two ways a target is identified, matching how each was actually found:
  - EXPLICIT_ID_TARGETS: exact Vetspire product ids, for 3 items spotted
    directly in a screenshot of Vetspire's own Products screen. Matched
    by id, not name -- the on-screen name wrapped across lines in the
    screenshot, so guessing its exact spacing would risk a wrong match
    (exactly the mistake the single-item test made: a fuzzy name match
    landed on a same-named sibling product instead of the intended one).
  - NAME_TARGETS: normalized product names (whitespace collapsed --
    Vetspire's real product names carry inconsistent double/trailing
    spaces, confirmed in scoutsync_uncategorized_services_probe.py's raw
    output), for the ~39 items identified from that probe's top-40
    uncategorized-by-revenue list (trailing 90 days). Resolved against
    ALL uncategorized dispensed_items rows (no date limit -- a product's
    identity doesn't depend on when it happened to be dispensed) to find
    every real Vetspire product id sharing that exact name.

Two entries are lower-confidence and flagged as such in the summary
(Gabapentin Solu / Doxycycline Solu -- "Solu" could mean an oral
solution, not necessarily injectable) -- assigned to Injection per the
original recommendation, trivially correctable via the same mutation if
a clinical review disagrees.

For each target: read its category before, call the mutation, read it
back again after (a fresh read, not the mutation's own response) to
confirm the write actually persisted -- same rigor as the single-item
test, just looped across every target. Continues past any single item's
failure so one bad id/name can't block the rest; every outcome is
printed, and a final summary tallies confirmed/no-change/error counts.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_bulk_category_apply.py
"""
import json, os, re, urllib.request, urllib.error

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

SERVICE        = "13601"
INJECTION      = "13597"
PHARMACEUTICAL = "13599"
MORTUARY       = "13602"
RADIOLOGY      = "13598"
LAB            = "4953"
DIET           = "13600"

# Ids spotted directly in a Vetspire Products screenshot -- matched by id,
# not name, since the on-screen name wrapped and exact spacing was unclear.
EXPLICIT_ID_TARGETS = {
    "697910": RADIOLOGY,  # Radiology - Radiography Interpretation (7-11)
    "697912": RADIOLOGY,  # Radiology - Radiography Interpretation (12-15); 3+ sites
    "628440": RADIOLOGY,  # Radiology - Addl View (Single Image)
}

# Names from the trailing-90-day top-40-uncategorized-by-revenue probe.
# Keys are matched after normalize() (whitespace-collapsed).
NAME_TARGETS = {
    "Exam - Urgent Care": SERVICE,
    "Exam - Recheck": SERVICE,
    "Euthanasia Services": SERVICE,
    "Ear Clean Level - Basic": SERVICE,
    "Exam - Euthanasia": SERVICE,
    "Bandage - Simple": SERVICE,
    "Exam - Technician": SERVICE,
    "Exam - Wellness": SERVICE,

    "Maropitant Inj 10 mg/ml": INJECTION,
    "Injection - IV/IM Administration": INJECTION,
    "Methadone Inj 10 mg/ml": INJECTION,
    "Gabapentin Solu 100 mg/ml": INJECTION,   # flagged -- "Solu" may mean oral solution
    "Ondansetron Inj 2 mg/ml": INJECTION,
    "Dexmedetomidine Inj 0.5 mg/ml": INJECTION,
    "Buprenorphine Inj 0.3 mg/ml": INJECTION,
    "Butorphanol Inj 10 mg/ml": INJECTION,
    "Atipamezole HCl Inj 5 mg/ml": INJECTION,
    "Doxycycline Solu 100 mg/ml": INJECTION,  # flagged -- "Solu" may mean oral solution

    "Proviable Paste Kit (Medium/Large Dog)": PHARMACEUTICAL,
    "Clavacillin 375 mg tablets": PHARMACEUTICAL,
    "Proviable Paste Kit (Cat/Small Dog)": PHARMACEUTICAL,
    "Clavacillin 250 mg tablets": PHARMACEUTICAL,
    "Gabapentin 300 mg capsules": PHARMACEUTICAL,
    "Clavacillin Susp 62.5 mg/ml (15 ml bottle)": PHARMACEUTICAL,
    "Gabapentin 100 mg capsules": PHARMACEUTICAL,
    "Endosorb Tablets": PHARMACEUTICAL,
    "Clavacillin 125 mg tablets": PHARMACEUTICAL,
    "Entyce 30 mg/ml (15 ml)": PHARMACEUTICAL,
    "Mirtazapine Transdermal Ointment 5 gm": PHARMACEUTICAL,
    "Cefpodoxime 200 mg tablets": PHARMACEUTICAL,
    "Robenacoxib 6 mg tablets (3/box)": PHARMACEUTICAL,
    "Carprofen 100 mg tablets": PHARMACEUTICAL,
    "Clavacillin 62.5 mg tablets": PHARMACEUTICAL,
    "Carprofen 75 mg tablets": PHARMACEUTICAL,

    "Cremation - Private": MORTUARY,
    "Cremation - Communal": MORTUARY,

    "Ultrasound - POCUS": RADIOLOGY,

    "Fecal Dx Profile with Giardia (24639)": LAB,

    "Hill's Canine Gastrointestinal Biome Chicken and Vegetable Stew (12.5oz)": DIET,
}


def normalize(name):
    return re.sub(r"\s+", " ", (name or "").strip())


NAME_TARGETS_NORMALIZED = {normalize(k): v for k, v in NAME_TARGETS.items()}


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": token,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"errors": [{"message": f"HTTP {e.code}: {body[:500]}"}]}


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.loads(r.read())
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def read_product_category(token, product_id):
    q = "query($id: ID) { product(id: $id) { id name productCategories { id name } } }"
    r = gql(token, q, {"id": product_id})
    if "errors" in r:
        return None, r["errors"]
    return (r.get("data") or {}).get("product") or {}, None


def apply_category(token, product_id, category_id, label):
    before, err = read_product_category(token, product_id)
    if err:
        print(f"  [{product_id}] {label}: SKIPPED -- could not read before-state: {json.dumps(err)[:300]}")
        return "error"
    mutation = """
    mutation($productId: ID, $categoryId: ID) {
      updateProductProductCategory(productId: $productId, productCategoryId: $categoryId) { id }
    }
    """
    result = gql(token, mutation, {"productId": product_id, "categoryId": category_id})
    if "errors" in result:
        print(f"  [{product_id}] {label}: MUTATION ERROR -- {json.dumps(result['errors'])[:300]}")
        return "error"
    after, err = read_product_category(token, product_id)
    if err:
        print(f"  [{product_id}] {label}: mutation ran but could not verify -- {json.dumps(err)[:300]}")
        return "unverified"
    after_ids = {str(c.get("id")) for c in (after.get("productCategories") or [])}
    if category_id in after_ids:
        before_names = [c.get("name") for c in (before.get("productCategories") or [])] if before else []
        print(f"  [{product_id}] {label}: OK -- was {before_names or '(none)'}, now includes the target category")
        return "confirmed"
    print(f"  [{product_id}] {label}: NO CHANGE DETECTED after mutation -- after={after.get('productCategories')}")
    return "no_change"


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip().removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    print("=== Resolving name-based targets against dispensed_items (all-time, no date limit) ===\n")
    rows = supa_get_all("dispensed_items", "select=vetspire_product_id,product_name&product_category_id=is.null")
    print(f"Fetched {len(rows)} uncategorized dispensed_items rows to resolve names against.\n")

    resolved = {}  # product_id -> (category_id, label)
    for pid, cat in EXPLICIT_ID_TARGETS.items():
        resolved[pid] = (cat, "(explicit id target)")

    seen_names = set()
    for r in rows:
        name = normalize(r.get("product_name"))
        pid = r.get("vetspire_product_id")
        if not pid or name not in NAME_TARGETS_NORMALIZED:
            continue
        seen_names.add(name)
        resolved.setdefault(pid, (NAME_TARGETS_NORMALIZED[name], name))

    missing = set(NAME_TARGETS_NORMALIZED) - seen_names
    if missing:
        print(f"-- {len(missing)} name targets had NO matching uncategorized row "
              f"(already fixed, or the name text doesn't match exactly) --")
        for m in sorted(missing):
            print(f"  {m!r}")

    print(f"\n=== Applying categories to {len(resolved)} distinct products ===\n")
    counts = {"confirmed": 0, "no_change": 0, "unverified": 0, "error": 0}
    for pid, (cat, label) in resolved.items():
        outcome = apply_category(token, pid, cat, label)
        counts[outcome] = counts.get(outcome, 0) + 1

    print("\n=== SUMMARY ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
