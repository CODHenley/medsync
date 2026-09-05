#!/usr/bin/env python3
"""
scoutsync_bulk_category_apply_round4.py
Round 4, user-authorized: applies category recommendations for the current
full uncategorized long tail (173 distinct names, 4134 instances, $149,586.52
across all locations/all-time -- see scoutsync_uncategorized_round4_probe.py)
to Vetspire, using updateProductProductCategory.

Same shape as rounds 1-2 (both since removed): names are matched after
normalize() (whitespace-collapsed) against every currently-uncategorized
dispensed_items row, all-time, resolved to real Vetspire product ids.

Category ids below are the CONFIRMED real ids from product_categories (see
round 4 probe output), not reused guesses from earlier rounds' partial
constant list -- several ids differ from what rounds 1-2 assumed (e.g. real
Radiology is 13598, real Service is 13601, matching round 2's constants, but
this round also uses several categories rounds 1-2 never needed: Ocular
Medications, Dermatology Medications, Prescription Diet, Prevention,
External Prescription, Mortuary Services, IDEXX In-house, General In-house
(lab), Vaccines - Feline).

Lower-confidence entries flagged in-line: two rabies specimen
submission/collection line items (no exact-matching reference-lab category
exists among the 18; filed under General In-house (lab) as the closest fit)
and Epinephrine Drops 10% (ambiguous route -- filed under Pharmaceutical).

For each target: read its category before, call the mutation, read it back
again after (a fresh read, not the mutation's own response) to confirm the
write actually persisted. Continues past any single item's failure so one
bad name/id can't block the rest; every outcome is printed, and a final
summary tallies confirmed/no-change/error counts.

Usage:
  VETSPIRE_API_TOKEN="..." python3 scoutsync_bulk_category_apply_round4.py
"""
import json, os, re, urllib.request, urllib.error

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

ANTECH             = "4951"
DERMATOLOGY        = "8491"
EXTERNAL_RX        = "13603"
LAB_GENERAL        = "4953"
IN_HOUSE_OTHER     = "4954"
IDEXX_INHOUSE      = "4949"
IDEXX_REFERENCE    = "4950"
INJECTION          = "13597"
MORTUARY           = "13602"
MSU_REFERENCE      = "4952"
OCULAR             = "8488"
PHARMACEUTICAL     = "13599"
PRESCRIPTION_DIET  = "13600"
PREVENTION         = "8489"
RADIOLOGY          = "13598"
SERVICE            = "13601"
VACCINES_CANINE    = "8494"
VACCINES_FELINE    = "8493"

# Names from the round-4 probe's full current uncategorized list (all-time,
# all locations). Keys are matched after normalize() (whitespace-collapsed).
NAME_TARGETS = {
    "Cytology with Microscopic Description (1 Site) - Standard (2801)": LAB_GENERAL,
    "(External Rx) Simparica Trio Chewable Tablet Dogs 44.1 to 88 lbs": EXTERNAL_RX,
    "Hill's i/d Canine Chicken and Vegetable Stew (12.5 oz)": PRESCRIPTION_DIET,
    "Hill's i/d Feline (5.5 oz)": PRESCRIPTION_DIET,
    "Senior Screen - IDEXX CBC (8659999)": IDEXX_INHOUSE,
    "Lymph Node Cytology - Standard (606)": LAB_GENERAL,
    "Panacur C Canine 1 g (3/box)": PHARMACEUTICAL,
    "(External Rx) Simparica Trio Chewable Tablet Dogs 22.1 to 44 lbs": EXTERNAL_RX,
    "Fenbendazole Susp 100 mg/ml": PHARMACEUTICAL,
    "Pelvis - VD/LAT R & L": RADIOLOGY,
    "Drain Placement - Closed Suction": SERVICE,
    "Pimobendan 2.5 mg tablets": PHARMACEUTICAL,
    "Hydrocodone 5 mg /Homatropine 1.5 mg tablets": PHARMACEUTICAL,
    "Exam - Health Certificate": SERVICE,
    "Senior Profile - IDEXX CBC (7809999)": IDEXX_INHOUSE,
    "Splint - Application": SERVICE,
    "Stifle - Lateral/CC": RADIOLOGY,
    "Zymox Otic with 1% Hydrocortisone (1.25 oz)": DERMATOLOGY,
    "Azithromycin 200 mg/5 ml Sus (30 ml bottle)": PHARMACEUTICAL,
    "(External Rx) Simparica Trio Chewable Tablet Dogs 5.6 to 11 lbs": EXTERNAL_RX,
    "Magic Mouth Wash (Oral Lidocaine, Diphenhydramine Syrup, Aluminum Hydroxide) / bottle": PHARMACEUTICAL,
    "Metamucil (Psyllium Husk Fiber) / tsp": PHARMACEUTICAL,
    "Ciprofloxacin 500 mg tablets": PHARMACEUTICAL,
    "Prazosin Tiny Tabs 0.5 mg": PHARMACEUTICAL,
    "Hill's c/d Feline Urinary Care (5.5 oz)": PRESCRIPTION_DIET,
    "No Flap Ear Wrap - Medium": SERVICE,
    "Famotidine 20 mg tablets": PHARMACEUTICAL,
    "Microchip Implantation": SERVICE,
    "Albon (Sulfadimethoxine) 250 mg tablets": PHARMACEUTICAL,
    "Domestic Health Certificate": SERVICE,
    "Ink Nose Print": MORTUARY,
    "Methimazole 5 mg tablets": PHARMACEUTICAL,
    "Metronidazole Benzoate Susp 50 mg/ml": PHARMACEUTICAL,
    "Magic Mouth Wash (Oral Lidocaine, Diphenhydramine Syrup, Aluminum Hydroxide) (bottle)": PHARMACEUTICAL,
    "Gabapentin Solu 50 mg/ml": PHARMACEUTICAL,
    "Furosemide Inj 50 mg/ml": INJECTION,
    "Clindamycin 75 mg capsules": PHARMACEUTICAL,
    "Hill's i/d Chicken & Veg Stew": PRESCRIPTION_DIET,
    "Ketamine HCl Inj 100 mg/ml": INJECTION,
    "Hydrocodone 5 mg /Homatropine 1.5 mg Solu / 5ml": PHARMACEUTICAL,
    "Endosorb Susp": PHARMACEUTICAL,
    "Bravecto Chewable Tablet Dogs > 44-88 lbs": PREVENTION,
    "Cytology with Microscopic Description (2 Sites) - Standard (2802)": LAB_GENERAL,
    "HealthChek Profile - Select (1)": IDEXX_INHOUSE,
    "Amp+Sulbactam Inj 30 mg/ml (1.5 g vial)": INJECTION,
    "Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Puppies & Small Dogs": PHARMACEUTICAL,
    "Marbofloxacin 25 mg tablets": PHARMACEUTICAL,
    "Royal Canin Feline SO (5.1 oz)": PRESCRIPTION_DIET,
    "Dextrose Solu Inj 50%": INJECTION,
    "Hill's i/d  Turkey (12.5 oz)": PRESCRIPTION_DIET,
    "Vanguard FVRCP Vaccine": VACCINES_FELINE,
    "Mometamax Sus (7.5 gm)": DERMATOLOGY,
    "Fluid Set Up & Admin - TGH Per Bag": SERVICE,
    "IDEXX CBC (375)": IDEXX_INHOUSE,
    "Ultrasound Guided  - FNA Mass": RADIOLOGY,
    "Vanguard RCP Vaccine": VACCINES_FELINE,
    "Clevor Opth Solu": OCULAR,
    "Tonometry, Recheck": SERVICE,
    "Tarsus - LAT/DP": RADIOLOGY,
    "Maropitant 160 mg tablets": PHARMACEUTICAL,
    "Bath/Grooming - Medical Treatment": SERVICE,
    "Urine Culture and MIC Susceptibility, Low Colony Count (4033)": LAB_GENERAL,
    "Azithromycin 250 mg tablets": PHARMACEUTICAL,
    "Seroma Lance & Drain": SERVICE,
    "Total Health Plus Profile with Free T4 (751)": IDEXX_INHOUSE,
    "Wood Urn - Engraving (3 lines)": MORTUARY,
    "Tick Removal (Single)": SERVICE,
    "Naloxone Inj 0.4 mg/ml": INJECTION,
    "Foreign Body Removal - Oral": SERVICE,
    "Amlodipine 2.5 mg tablets": PHARMACEUTICAL,
    "Ear Clean Level - Advanced": SERVICE,
    "Urinary - Indwelling Collection System Set-Up": SERVICE,
    "Bravecto Chewable Tablet Dogs > 22-44 lbs": PREVENTION,
    "Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Medium Dogs": PHARMACEUTICAL,
    "Mirtazapine 7.5 mg tablets": PHARMACEUTICAL,
    "Carpus - LAT/DP": RADIOLOGY,
    "Diphenhydramine 50 mg capsules": PHARMACEUTICAL,
    "No Flap Ear Wrap - Large": SERVICE,
    "No Flap Ear Wrap - Small": SERVICE,
    "Diphenhydramine 25 mg capsules": PHARMACEUTICAL,
    "Thorax - DV/LAT R&L": RADIOLOGY,
    "Treatment Demonstration": SERVICE,
    "Furosemide Syrup 1% (10 mg/ml)": PHARMACEUTICAL,
    "Doxycycline 100 mg capsules": PHARMACEUTICAL,
    "Mometamax Sus (7.5 g)": DERMATOLOGY,
    "Foreign Body Removal - Skin/Paw": SERVICE,
    "SNAP Giardia Test": LAB_GENERAL,
    "Total Health Profile - Select (1013)": IDEXX_INHOUSE,
    "Tech Time - One-on-One/15 min": SERVICE,
    "Bravecto Chewable Tablet Dogs > 9.9-22 lbs": PREVENTION,
    "Furosemide 12.5 mg tablets": PHARMACEUTICAL,
    "Exam - Litter": SERVICE,
    "Entyce 30 mg/ml (30 ml)": PHARMACEUTICAL,
    "Rabies Spec Collect/Submission (Cook County)": LAB_GENERAL,  # flagged -- no exact reference-lab category fits
    "Cystocentesis - Therapeutic": SERVICE,
    "Epinephrine Inj 1 mg/ml": INJECTION,
    "Rabies Spec Submission - UIUC VDL": LAB_GENERAL,  # flagged -- no exact reference-lab category fits
    "HealthChek Profile - IDEXX CBC (19999)": IDEXX_INHOUSE,
    "Albuterol HFA 90 mcg": PHARMACEUTICAL,
    "Diclofenac Opthalmic Solu 0.1% (5 ml)": OCULAR,
    "Urinary Catheter - Indwelling (Male)": SERVICE,
    "Simparica Trio Chewable Tablet Dogs 2.8 to 5.5 lbs": PREVENTION,
    "Mass Excision": SERVICE,
    "Amputate Digit": SERVICE,
    "Bravecto Chewable Tablet Dogs 4.5-9.9 lbs": PREVENTION,
    "Tibia/Fibula - LAT/CC": RADIOLOGY,
    "Radius/Ulna - LAT/CC": RADIOLOGY,
    "Leptospira spp. Panel - Canine (3569)": LAB_GENERAL,
    "Levetiracetam 750 mg tablets": PHARMACEUTICAL,
    "Hand Cautery": SERVICE,
    "Fur Clipping - Addl": SERVICE,
    "Drain Placement - Penrose": SERVICE,
    "Apomorphine HCl Inj 1 mg/mL": INJECTION,
    "Extended Stabilization": SERVICE,
    "Foreign Body Removal, Simple": SERVICE,
    "Exam - Litter (Each Addl)": SERVICE,
    "Librela 20 mg/mL (66.2-88.2 lb) - In-house use ONLY": INJECTION,
    "Cuterebra Removal (Single)": SERVICE,
    "Foreign Body Removal - Conjunctival": SERVICE,
    "Diphenhydramine Syrup 12.5 mg/5 ml": PHARMACEUTICAL,
    "Patient Heat Support": SERVICE,
    "Hospitalization - Outpatient": SERVICE,
    "International Health Certificate": SERVICE,
    "(External Rx) Simparica Trio Chewable Tablet Dogs 88.1 to 132 lbs": EXTERNAL_RX,
    "Zonisamide - Cornell": PHARMACEUTICAL,
    "Skin Biopsy": LAB_GENERAL,
    "Skin Scrape (2+ Sites)": LAB_GENERAL,
    "Furosemide 20 mg tablets": PHARMACEUTICAL,
    "Endotracheal Tube Placement": SERVICE,
    "Levetiracetam Solu 100 mg/ml (16 oz)": PHARMACEUTICAL,
    "Bravecto Chewable Tablet Dogs > 88-123 lbs": PREVENTION,
    "Foreign Body Removal - Aural": SERVICE,
    "Foreign Body Removal - Corneal": SERVICE,
    "Gastric Decompression - Trocar": SERVICE,
    "Acepromazine Inj 10 mg/ml": INJECTION,
    "Ultrasound - Mass": RADIOLOGY,
    "Rectal Prolapse - Manual Reduction": SERVICE,
    "Calcium Gluconate 10% Inj (100 mg/ml)": INJECTION,
    "VetStat Electrolyte 8 Plus": LAB_GENERAL,
    "Fentanyl Transdermal 100 mcg/hr Patch": PHARMACEUTICAL,
    "Standard Shipping & Handling": SERVICE,
    "Flumazenil Inj  0.1 mg/ml": INJECTION,
    "Ink Paw Print": MORTUARY,
    "Medication Administration (Flea/Tick Treatment)": PREVENTION,
    "Levetiracetam 250 mg tablets": PHARMACEUTICAL,
    "Nitro-Bid Ointment 2%": PHARMACEUTICAL,
    "Epinephrine Drops 10%": PHARMACEUTICAL,  # flagged -- ambiguous route
    "Fatal-Plus Solu Inj 390 mg/ml": INJECTION,
    "Endotracheal Tube - 7.0 mm Cuffed": SERVICE,
    "Remembrance Urn - Standard": MORTUARY,
    "External Prescription": EXTERNAL_RX,
    "Fecal Dropoff - Completion": SERVICE,
    "External Prescription, Request": EXTERNAL_RX,
    "Interpretation, Radiography": RADIOLOGY,
    "Hill's Onc Canine 12.5 oz": PRESCRIPTION_DIET,
    "Humerus - LAT/CC": RADIOLOGY,
    "Heartworm Antigen by ELISA - Feline Add-on (12371)": LAB_GENERAL,
    "Senior Profile - Chem 27 w/SDMA Test, CBC Select, Total T4, UA (2663)": IDEXX_INHOUSE,
    "Calcium Alginate": SERVICE,
    "Splint - Quick Splint (Medium LHL/RHL)": SERVICE,
    "(OTC) Famotidine (Pepcid) 20mg Tablets/Capsules": PHARMACEUTICAL,
    "Nasogastric Tube - 5fr x 55 cm MILA": SERVICE,
    "Wildlife/Stray": SERVICE,
    "Cast - Vetcast 2in": SERVICE,
    "Urinary Catheter - Foley 6fr x 60 cm w/ stylet": SERVICE,
    "Red Rubber - 8fr x 22in": SERVICE,
    "Splint - Quick Splint (Small LFL/RFL)": SERVICE,
    "Drain - Jackson Pratt 15fr": SERVICE,
    "Larynx - VD/LAT": RADIOLOGY,
    "Red Rubber - 3.5fr x 16in": SERVICE,
    "Endotracheal Tube - 7.5 mm Cuffed": SERVICE,
    "(External Rx) Royal Canin Hydrolyzed Protein Diet, Canine, Dry and/or Wet.": EXTERNAL_RX,
    "Royal Canin Feline SO (3 oz)": PRESCRIPTION_DIET,
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
