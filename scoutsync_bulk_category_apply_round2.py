#!/usr/bin/env python3
"""
scoutsync_bulk_category_apply_round2.py
Round 2, user-authorized: applies the second batch of category
recommendations (the long tail surfaced after round 1's fix was
confirmed working -- 19,672 uncategorized rows/$1,362,174 dropped to
5,075 rows/$167,320 across 170 distinct names once dispensed_items was
re-backfilled) to Vetspire, using updateProductProductCategory.

Same shape as scoutsync_bulk_category_apply.py (round 1, since removed):
names are matched after normalize() (whitespace-collapsed) against every
currently-uncategorized dispensed_items row, all-time, resolved to real
Vetspire product ids. No explicit-id targets this round -- every item was
identified from probe data (not a screenshot), so the names are already
exact.

Three lower-confidence entries, flagged in-line: Prednisolone Solu and
Lactulose Solu ("Solu" could mean oral solution -- filed under
Pharmaceutical here, which is the correct bucket either way, unlike
round 1's Injection guesses); Misc Medications (a genuine catch-all with
no better fit among the 18 real categories).

For each target: read its category before, call the mutation, read it
back again after (a fresh read, not the mutation's own response) to
confirm the write actually persisted. Continues past any single item's
failure so one bad name/id can't block the rest; every outcome is
printed, and a final summary tallies confirmed/no-change/error counts.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_bulk_category_apply_round2.py
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
OCULAR         = "8488"

# Names from the round-2 probe's top-80 uncategorized-by-revenue list
# (180-day window, post-re-backfill). Keys are matched after normalize()
# (whitespace-collapsed).
NAME_TARGETS = {
    "Catheterization - Peripheral IV": SERVICE,
    "Bandage - Temporary": SERVICE,
    "Enema": SERVICE,
    "Bandage - Tie Over (Change)": SERVICE,
    "Nail Trim": SERVICE,
    "Bandage - Complex": SERVICE,
    "Abscess Lance & Drain": SERVICE,
    "Bandage - Tie Over (Initial Placement)": SERVICE,
    "Surgical Pack (Small)": SERVICE,
    "Foot Soak": SERVICE,
    "Ear Clean Level - Intermediate": SERVICE,
    "Preputial Exam/Flush": SERVICE,
    "Cast Application - Delta Light Cast/Splint": SERVICE,
    "Exam - Urgent Care": SERVICE,  # tiny residual (6x/$810) left over from round 1's fix
    "Deobstipate - Digital/15 min": SERVICE,
    "Urinary Catheter - Collection (Male)": SERVICE,
    "Sanitary Clip/Clean": SERVICE,
    "Activated Charcoal Administration": SERVICE,
    "Ultrasound Guided - Cystocentesis": SERVICE,  # user correction: this is a procedure, not imaging/interpretation

    "Anesthesia - Local Block Administration": INJECTION,
    "Alfaxalone Inj 10 mg/ml": INJECTION,
    "Apomorphine HCl 3 mg/ml": INJECTION,
    "Diphenhydramine Inj 50 mg/ml": INJECTION,
    "Solensia": INJECTION,
    "Famotidine Inj 10 mg/mL": INJECTION,
    "Dexamethasone-SP Inj 4 mg/ml": INJECTION,
    "Lidocaine HCl 2% Inj (20 mg/ml)": INJECTION,
    "Injection Fee": INJECTION,
    "Zenalpha 0.5 mg/ml": INJECTION,
    "Midazolam Inj 5 mg/ml": INJECTION,

    "Carprofen 25 mg tablets": PHARMACEUTICAL,
    "Gabapentin 100 mg QuadTabs": PHARMACEUTICAL,
    "Maropitant 16 mg tablets": PHARMACEUTICAL,
    "Ondansetron 8 mg tablets": PHARMACEUTICAL,
    "Ondansetron 4 mg tablets": PHARMACEUTICAL,
    "Maropitant 60 mg tablets": PHARMACEUTICAL,
    "Metronidazole Benzoate Sus 100 mg/ml": PHARMACEUTICAL,
    "Meloxicam Susp 0.5 mg/ml": PHARMACEUTICAL,
    "Enrofloxacin 136 mg tablets": PHARMACEUTICAL,
    "Trazodone 100 mg tablets": PHARMACEUTICAL,
    "Metronidazole Tiny Tabs 50 mg tablets": PHARMACEUTICAL,
    "Cephalexin 500 mg capsules": PHARMACEUTICAL,
    "Doxycycline 100 mg tablets": PHARMACEUTICAL,
    "Maropitant 24 mg tablets": PHARMACEUTICAL,
    "Metronidazole 250 mg tablets": PHARMACEUTICAL,
    "PredniSONE 10 mg tablets": PHARMACEUTICAL,
    "Elura 20 mg/ml (15 ml)": PHARMACEUTICAL,
    "Meloxicam Susp 1.5 mg/ml": PHARMACEUTICAL,
    "Prednisolone Solu 15 mg/ 5 ml": PHARMACEUTICAL,  # flagged -- "Solu" likely oral solution
    "Cephalexin 250 mg capsules": PHARMACEUTICAL,
    "Clindamycin 150 mg capsules": PHARMACEUTICAL,
    "Trazodone 50 mg tablets": PHARMACEUTICAL,
    "Chlorhexidine Solution 2% (8 oz)": PHARMACEUTICAL,
    "Clindamycin Susp 25 mg/ml (20 ml bottle)": PHARMACEUTICAL,
    "Panacur C Canine 4 g (3/box)": PHARMACEUTICAL,
    "Prednisolone 5 mg tablets": PHARMACEUTICAL,
    "Lactulose Solu 10 g/15 ml": PHARMACEUTICAL,  # flagged -- "Solu" likely oral solution
    "Methocarbamol 500 mg tablets": PHARMACEUTICAL,
    "Metronidazole 500 mg tablets": PHARMACEUTICAL,
    "Pyrantel Pamoate (50 mg/ml)": PHARMACEUTICAL,
    "Vitamin K-1 50 mg tablets": PHARMACEUTICAL,
    "Misc Medications": PHARMACEUTICAL,  # flagged -- genuine catch-all, no better fit among the 18 categories
    "Viralys Powder": PHARMACEUTICAL,
    "Panacur C Canine 2 g  (3/box)": PHARMACEUTICAL,
    "Famotidine 10 mg tablets": PHARMACEUTICAL,
    "Drontal (Praziquantel/Pyrantel Pamoate) for Cats and Kittens": PHARMACEUTICAL,
    "Yunnan Baiyao (16/box)": PHARMACEUTICAL,
    "Sucralfate 1 gm tablets": PHARMACEUTICAL,
    "ToxiBan (without Sorbitol)": PHARMACEUTICAL,
    "Veraflox Susp 25 mg/ml (15 ml bottle)": PHARMACEUTICAL,

    "Hill's Feline Gastrointestinal Biome (2.9 oz)": DIET,
    "Hill's i/d Canine Low Fat Stew (12.5 oz)": DIET,

    "Thorax - VD or DV/LAT R & L": RADIOLOGY,
    "Elbow - LAT/CC": RADIOLOGY,

    "BNP Opthalmic Ointment (3.5 gm)": OCULAR,
    "Autogenous Serum Eye Drops": OCULAR,

    "Schirmer Tear Test (STT)": LAB,

    "Clay Paw Print - Addl": MORTUARY,
    "Metal Urn - Engraving (3 lines)": MORTUARY,
    "Ink Paw Print": MORTUARY,
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
