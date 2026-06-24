#!/usr/bin/env python3
"""
backfill_ndcs.py
For every product in Supabase's products table that has no NDC, query the
FDA OpenFDA drug/ndc API to find a match and backfill the NDC.

FDA API: https://api.fda.gov/drug/ndc.json  (free, no key required)
Search strategy per product:
  1. Exact brand_name match
  2. Exact generic_name match
  3. Partial brand_name match (first significant word)
  4. Partial generic_name match

Skips External Rx items, lab tests, diagnostic kits, and supplies
(catheters, splints, drains, etc.) — those don't have NDCs.

Usage:
    python3 backfill_ndcs.py [--dry-run]
"""
import sys, json, os, time, urllib.request, urllib.parse, re

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
FDA_URL  = "https://api.fda.gov/drug/ndc.json"

DRY_RUN = "--dry-run" in sys.argv

# ── Skip patterns — items that will never have an NDC ────────────────────────
SKIP_PATTERNS = [
    r"^\(External Rx\)",           # external prescriptions
    r"^SNAP ",                     # IDEXX SNAP tests
    r"^Catalyst ",                 # IDEXX Catalyst slides
    r"RealPCR",                    # PCR panels
    r"Antigen by Latex",           # serology tests
    r"^Cast\b",                    # casting supplies
    r"^Drain\b",                   # surgical drains
    r"^Red Rubber\b",              # catheters
    r"^Nasogastric Tube",
    r"^Urinary Catheter",
    r"^Splint\b",
    r"^No Flap Ear Wrap",
    r"^Urine Collection",
    r"Microchip Implant",
    r"Spec Collect",               # specimen collection fees
    r"Implantation",
    r"\bLabel\b",                  # label rolls / supplies
    r"Per Roll",
    r"^Hill's\b",                  # prescription diets — no NDC
    r"^Royal Canin\b",
    r"^Science Diet\b",
    r"^Purina\b",
    r"Diet,",
    r"\bDiet\b.*\boz\b",
    r"^Microchip\b",
    r"^Anemia\b",                  # PCR/lab panels
    r"Panel[—-]",
    r"^Cryptococcus\b",
    r"Rabies Spec",
    r"Collection Kit",
    r"^No Flap",
    r"^TUMS\b",                    # OTC human products unlikely to match vet NDC
    r"^Glycerin\b",
    r"Ear Wrap",
    r"Bravecto",                   # Zoetis vet-only — often missing from FDA DB
    r"Vetcast",
    r"^Clevor\b",                  # ropinirole vet product — may not be in FDA
]

def should_skip(name):
    for pat in SKIP_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False

# ── Supabase helpers ──────────────────────────────────────────────────────────
SUPA_H = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json",
}

def supa_get(path):
    req = urllib.request.Request(SUPA_URL + path, headers=SUPA_H)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def supa_patch(path, body):
    data = json.dumps(body).encode()
    h = {**SUPA_H, "Prefer": "return=minimal"}
    req = urllib.request.Request(SUPA_URL + path, data=data, method="PATCH", headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status

# ── FDA OpenFDA helpers ───────────────────────────────────────────────────────
def fda_search(field, value, limit=3):
    """Query FDA NDC database. Returns list of product records."""
    q = f'{field}:"{urllib.parse.quote(value)}"'
    url = f"{FDA_URL}?search={q}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "medsync-ndc-backfill/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return data.get("results") or []
    except urllib.error.HTTPError:
        return []   # 404 = no results, 500 = bad query — either way skip
    except Exception:
        return []

def extract_ndc(result):
    """Pull the best NDC from an FDA result record."""
    # product_ndc is in format "XXXXX-XXXX" (labeler-product, no package segment)
    return result.get("product_ndc") or ""

def clean_name_for_search(name):
    """Strip dosage/form info to get the core drug name for searching."""
    # Remove common suffixes: "10 mg/ml", "Inj", "tablets", "Solu", etc.
    name = re.sub(r'\s+\d[\d.]*\s*(mg|mcg|ml|g|%|units?|USP)[/\w]*', '', name, flags=re.I)
    name = re.sub(r'\s+(inj|tablets?|tabs?|solu|solution|ointment|oral|opth|susp?|caps?|chewable|powder)\b.*', '', name, flags=re.I)
    name = re.sub(r'\s*\(.*\)', '', name)   # remove parentheticals
    name = name.strip()
    return name

def find_ndc(product_name):
    """Try multiple FDA search strategies, return (ndc, matched_name) or (None, None)."""
    clean = clean_name_for_search(product_name)

    strategies = [
        ("brand_name",   product_name),
        ("generic_name", product_name),
        ("brand_name",   clean),
        ("generic_name", clean),
    ]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in strategies:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    for field, term in unique:
        if not term or len(term) < 3:
            continue
        results = fda_search(field, term)
        if results:
            # Prefer veterinary products, then human — pick first result
            vet = [r for r in results if "veterinary" in (r.get("product_type") or "").lower()]
            best = vet[0] if vet else results[0]
            ndc = extract_ndc(best)
            matched = best.get("brand_name") or best.get("generic_name") or term
            if ndc:
                return ndc, matched, field
        time.sleep(0.08)   # stay under FDA rate limit (~240 req/min)

    return None, None, None

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"=== NDC Backfill from FDA Database {'[DRY RUN] ' if DRY_RUN else ''}===\n")

# Fetch all products from Supabase that have no NDC
print("Fetching products without NDC from Supabase…")
products = supa_get("/rest/v1/products?select=id,name,ndc&ndc=is.null&limit=2000")
also_empty = supa_get("/rest/v1/products?select=id,name,ndc&ndc=eq.&limit=2000")
products = products + also_empty
print(f"  {len(products)} products without NDC\n")

found     = []
not_found = []
skipped   = []

for i, p in enumerate(products):
    name = (p.get("name") or "").strip()
    pid  = p.get("id")

    if not name or not pid:
        continue

    if should_skip(name):
        skipped.append(name)
        continue

    ndc, matched_name, match_field = find_ndc(name)

    if ndc:
        confidence = "exact" if name.lower() in (matched_name or "").lower() else "fuzzy"
        print(f"  ✓ {name[:55]:<55}  NDC: {ndc:<15}  ({confidence} match on {match_field})")
        found.append({"id": pid, "name": name, "ndc": ndc, "matched": matched_name, "confidence": confidence})
        if not DRY_RUN:
            try:
                supa_patch(f"/rest/v1/products?id=eq.{pid}", {"ndc": ndc})
            except Exception as e:
                print(f"    ✗ Supabase update failed: {e}")
    else:
        print(f"  ✗ {name[:55]}")
        not_found.append(name)

    # Brief pause every 20 requests to be safe with FDA rate limits
    if i % 20 == 19:
        time.sleep(1)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  Found NDC:     {len(found)}")
print(f"  Not found:     {len(not_found)}")
print(f"  Skipped:       {len(skipped)}  (supplies/labs/external Rx — no NDC expected)")
if DRY_RUN:
    print(f"\n  DRY RUN — no Supabase records updated")
else:
    print(f"\n  Supabase updated for {len(found)} products")

if not_found:
    print(f"\nProducts with no NDC match in FDA database:")
    for n in not_found:
        print(f"  - {n}")

print("\nDone.")
