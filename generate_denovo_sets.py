#!/usr/bin/env python3
"""
Fetch Scout's actual product catalog from Supabase and generate
calibrated DENOVO_SETS for the New Location Setup screen.

Run from your Mac:
  python3 generate_denovo_sets.py

Output is ready-to-paste JavaScript for medsync_newlocation_live.html
"""

import json, urllib.request, urllib.parse, sys

SUPA_URL = 'https://aemkdummdrmxtwrkggjw.supabase.co'
SUPA_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s'

HEADERS = {
    'apikey': SUPA_KEY,
    'Authorization': f'Bearer {SUPA_KEY}',
    'Content-Type': 'application/json',
}

def fetch(path):
    req = urllib.request.Request(SUPA_URL + path, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def main():
    print("Fetching products from Supabase...", file=sys.stderr)
    products = fetch(
        '/rest/v1/products'
        '?select=id,name,category,ndc,vendor,dispensing_unit,package_size,unit_price,qty_min,qty_max,supply_type'
        '&order=category,name'
        '&limit=1000'
    )
    print(f"  {len(products)} products loaded", file=sys.stderr)

    # Also fetch lots to see what's actually stocked and in what quantities at Wheaton
    # (most recently opened location = best proxy for opening order)
    lots = fetch(
        '/rest/v1/lots'
        '?select=product_id,qty_received,qty_remaining,location_id'
        '&status=eq.Active'
        '&limit=2000'
    )
    print(f"  {len(lots)} active lots loaded", file=sys.stderr)

    # Build product lookup
    prod_by_id = {p['id']: p for p in products}

    # Aggregate qty_received per product across all locations
    # (sum gives us a sense of overall stocking levels)
    from collections import defaultdict
    qty_by_product = defaultdict(int)
    for lot in lots:
        pid = lot.get('product_id')
        qty = lot.get('qty_received') or 0
        if pid:
            qty_by_product[pid] += qty

    # Map Supabase categories to denovo section labels
    CAT_MAP = {
        'Controlled Substances': ('Controlled Substances', 'Pharmacy'),
        'Injectable': ('Injectables', 'Pharmacy'),
        'Injectables': ('Injectables', 'Pharmacy'),
        'Antibiotic': ('Antibiotics', 'Pharmacy'),
        'Antibiotics': ('Antibiotics', 'Pharmacy'),
        'Analgesic': ('Analgesia', 'Pharmacy'),
        'Analgesia': ('Analgesia', 'Pharmacy'),
        'Preventative': ('Preventatives', 'Pharmacy'),
        'Preventatives': ('Preventatives', 'Pharmacy'),
        'Diagnostic': ('Diagnostics', 'Laboratory'),
        'Diagnostics': ('Diagnostics', 'Laboratory'),
        'Vaccine': ('Vaccines', 'Pharmacy / Cold Storage'),
        'Vaccines': ('Vaccines', 'Pharmacy / Cold Storage'),
        'Fluid': ('IV Fluids', 'Treatment'),
        'IV Fluids': ('IV Fluids', 'Treatment'),
        'Fluids': ('IV Fluids', 'Treatment'),
        'GI': ('GI / Gastrointestinal', 'Pharmacy'),
        'Gastrointestinal': ('GI / Gastrointestinal', 'Pharmacy'),
        'Dermatology': ('Dermatology', 'Pharmacy'),
        'Ophthalmic': ('Ophthalmics', 'Pharmacy'),
        'Ophthalmics': ('Ophthalmics', 'Pharmacy'),
        'Supplement': ('Supplements', 'Pharmacy'),
        'Supplements': ('Supplements', 'Pharmacy'),
        'Equipment': ('Medical Equipment', 'Treatment'),
        'Medical Equipment': ('Medical Equipment', 'Treatment'),
        'Dental': ('Dental', 'Pharmacy'),
        'Prescription Diet': ('Prescription Diets', 'Pharmacy'),
        'Prescription Diets': ('Prescription Diets', 'Pharmacy'),
        'Sedation': ('Sedation / Anesthesia', 'Pharmacy'),
        'Anesthesia': ('Sedation / Anesthesia', 'Pharmacy'),
        'Sedation / Anesthesia': ('Sedation / Anesthesia', 'Pharmacy'),
        'Cardiology': ('Cardiology', 'Pharmacy'),
        'Endocrine': ('Endocrine', 'Pharmacy'),
        'Miscellaneous': ('Miscellaneous', 'Pharmacy'),
        'Other': ('Miscellaneous', 'Pharmacy'),
    }

    SKIP_CATS = {'Medical Equipment', 'Equipment'}  # keep equipment hardcoded
    SKIP_SUPPLY = {'equipment', 'capital'}

    def qty_for_uc(p):
        """Opening qty for an Urgent Care from Scout's stocking data."""
        pid = p['id']
        actual = qty_by_product.get(pid, 0)
        qty_min = p.get('qty_min') or 0
        qty_max = p.get('qty_max') or 0
        # Use qty_min as opening qty if set, otherwise derive from actual stock
        if qty_min and qty_min > 0:
            return int(qty_min)
        if actual > 0:
            # Scale: actual is sum across ~4 locations, so /4 rounded up to nearest unit
            per_loc = max(1, round(actual / 4))
            return per_loc
        return 1

    # Build UC and ER items from actual products
    uc_items = []
    seen_names = set()

    for p in products:
        raw_cat = (p.get('category') or '').strip()
        supply = (p.get('supply_type') or '').lower()

        if raw_cat in SKIP_CATS:
            continue
        if supply in SKIP_SUPPLY:
            continue
        if not raw_cat:
            continue

        cat_info = CAT_MAP.get(raw_cat)
        if not cat_info:
            # Try case-insensitive match
            cat_info = next((v for k, v in CAT_MAP.items() if k.lower() == raw_cat.lower()), None)
        if not cat_info:
            cat_info = ('Miscellaneous', 'Pharmacy')

        js_cat, js_section = cat_info

        name = p['name'] or ''
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        ndc = p.get('ndc') or ''
        qty = qty_for_uc(p)

        uc_items.append({
            'cat': js_cat,
            'name': name,
            'sku': ndc,
            'qty': qty,
            'section': js_section,
        })

    # Sort by category then name
    CAT_ORDER = [
        'Medical Equipment', 'Diagnostics', 'IV Fluids',
        'Controlled Substances', 'Sedation / Anesthesia', 'Injectables',
        'Antibiotics', 'Analgesia', 'GI / Gastrointestinal', 'Ophthalmics',
        'Dermatology', 'Endocrine', 'Cardiology', 'Vaccines',
        'Preventatives', 'Supplements', 'Dental', 'Prescription Diets', 'Miscellaneous',
    ]
    def sort_key(item):
        try:
            return (CAT_ORDER.index(item['cat']), item['name'].lower())
        except ValueError:
            return (99, item['name'].lower())

    uc_items.sort(key=sort_key)

    def js_item(item, qty_override=None):
        qty = qty_override if qty_override is not None else item['qty']
        name = item['name'].replace("'", "\\'")
        sku  = item['sku'].replace("'", "\\'")
        return f"  {{cat:'{item['cat']}',name:'{name}',sku:'{sku}',qty:{qty},section:'{item['section']}'}}"

    # Separate preventatives (UC keeps, ER drops)
    uc_non_prev = [i for i in uc_items if i['cat'] != 'Preventatives']
    uc_prev     = [i for i in uc_items if i['cat'] == 'Preventatives']
    equip_cats  = {'Medical Equipment'}

    print("\n// ─────────────────────────────────────────────────────────────────")
    print("// AUTO-GENERATED from Scout Supabase products — paste into")
    print("// medsync_newlocation_live.html replacing the DENOVO_SETS block")
    print("// ─────────────────────────────────────────────────────────────────")
    print()

    # UC set
    print("DENOVO_SETS.urgent_care = [")
    # Hardcoded equipment block first
    print("  // ── Medical Equipment (hardcoded — not in products table) ──")
    UC_EQUIPMENT = [
        ("Medical Equipment","Midmark Multiparameter Anesthesia Monitor","PM-9000",2,"Surgery / Treatment"),
        ("Medical Equipment","Wildcat 750 Anesthesia Machine","Vetamac",1,"Surgery"),
        ("Medical Equipment","IDEXX Catalyst One Chemistry Analyzer","IDEXX Catalyst One",1,"Laboratory"),
        ("Medical Equipment","IDEXX ProCyte One Hematology Analyzer","IDEXX ProCyte One",1,"Laboratory"),
        ("Medical Equipment","IDEXX SediVue Dx Urinalysis Analyzer","IDEXX SediVue Dx",1,"Laboratory"),
        ("Medical Equipment","Covetrus ProMAX Infusion Pump","Covetrus ProMAX",1,"Treatment / ICU"),
        ("Medical Equipment","VET-DOP 2 Doppler Blood Pressure","Vmed VET-DOP 2",1,"Treatment"),
        ("Medical Equipment","TonoVet Plus Tonometer","TonoVet Plus",1,"Exam / Treatment"),
        ("Medical Equipment","T-Top 10 Veterinary Autoclave","Tuttnauer T-Top 10",1,"Surgery Prep"),
        ("Medical Equipment","Masimo Rad-57 Pulse CO-Oximeter","Masimo Rad-57",1,"Treatment / ICU"),
        ("Medical Equipment","MidMark Platform Scale","MidMark 07-893-6514",2,"Exam Rooms"),
        ("Medical Equipment","AlphaTRAK 2 Glucometer","AlphaTRAK 2",2,"Treatment / Lab"),
    ]
    for cat,name,sku,qty,sec in UC_EQUIPMENT:
        print(f"  {{cat:'{cat}',name:'{name}',sku:'{sku}',qty:{qty},section:'{sec}'}},")
    print("  // ── Medications & consumables from Scout catalog ──")
    for item in uc_non_prev:
        print(js_item(item) + ',')
    print("  // ── Preventatives (UC only) ──")
    for item in uc_prev:
        print(js_item(item) + ',')
    print("];")

    print()

    # ER set
    print("// ER: same types as UC, no preventatives, 2x medication quantities")
    print("const ER_EQUIPMENT_CATS = new Set(['Medical Equipment']);")
    print("DENOVO_SETS.er = [")
    print("  // ── Medical Equipment (same as UC + ICU additions) ──")
    for cat,name,sku,qty,sec in UC_EQUIPMENT:
        print(f"  {{cat:'{cat}',name:'{name}',sku:'{sku}',qty:{qty},section:'{sec}'}},")
    ER_EXTRA_EQUIP = [
        ("Medical Equipment","Covetrus ProMAX Syringe Pump","Covetrus ProMAX Syringe",2,"ICU"),
        ("Medical Equipment","EMMA Capnograph (EtCO2 Monitor)","Masimo EMMA",2,"Surgery / ICU"),
    ]
    for cat,name,sku,qty,sec in ER_EXTRA_EQUIP:
        print(f"  {{cat:'{cat}',name:'{name}',sku:'{sku}',qty:{qty},section:'{sec}'}},")
    print("  // ── Medications & consumables (2x UC quantities) ──")
    for item in uc_non_prev:
        print(js_item(item, qty_override=item['qty'] * 2) + ',')
    print("  // ── Additional critical care medications ──")
    ER_EXTRA_MEDS = [
        ("Injectables","Epinephrine 1mg/mL","400002",4,"Pharmacy"),
        ("Injectables","Atropine Injection","641602110",4,"Pharmacy"),
        ("Controlled Substances","Propofol 10mg/mL","1117",8,"Pharmacy"),
        ("Controlled Substances","Fentanyl 50mcg/mL","50383004316",4,"Pharmacy"),
    ]
    for cat,name,sku,qty,sec in ER_EXTRA_MEDS:
        print(f"  {{cat:'{cat}',name:'{name}',sku:'{sku}',qty:{qty},section:'{sec}'}},")
    print("];")

    print(file=sys.stderr)
    print(f"Done — {len(uc_items)} products mapped ({len(uc_prev)} preventatives, {len(uc_non_prev)} medications/consumables)", file=sys.stderr)

if __name__ == '__main__':
    main()
