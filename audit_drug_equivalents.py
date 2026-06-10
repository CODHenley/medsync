#!/usr/bin/env python3
"""
audit_drug_equivalents.py
--------------------------
Pulls all products from Supabase and identifies brand/generic/scientific
name equivalents (e.g. Cerenia = Emprev = Maropitant).

For each equivalence group found, checks whether qty_min/qty_max are
consistent and flags mismatches.

Output: prints a report + saves audit_drug_equivalents.csv

Usage:
    python3 audit_drug_equivalents.py
"""

import json
import csv
import urllib.request

# ── Config ────────────────────────────────────────────────────────────────────
SUPA_URL = 'https://aemkdummdrmxtwrkggjw.supabase.co'
SUPA_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s'

# ── Veterinary drug equivalence map ──────────────────────────────────────────
# Format: 'canonical_scientific_name': ['brand1', 'brand2', 'generic_label', ...]
# All strings lowercase; matched via CONTAINS (substring)
DRUG_GROUPS = {
    'maropitant': ['cerenia', 'emprev', 'maropitant'],
    'meloxicam': ['metacam', 'meloxicam', 'loxicom', 'inflacam', 'rheumocam'],
    'carprofen': ['rimadyl', 'carprofen', 'novox', 'vetprofen', 'zinecarp', 'canidryl'],
    'gabapentin': ['gabapentin', 'neurontin'],
    'buprenorphine': ['buprenorphine', 'simbadol', 'buprenex', 'vetergesic'],
    'acepromazine': ['acepromazine', 'acepromazin', 'promace'],
    'dexmedetomidine': ['dexmedetomidine', 'dexdomitor', 'sileo', 'dexdormitor'],
    'medetomidine': ['medetomidine', 'domitor'],
    'atipamezole': ['atipamezole', 'antisedan'],
    'ketamine': ['ketamine', 'ketaset', 'vetaket', 'ketaved'],
    'propofol': ['propofol', 'rapinovet', 'propovet', 'propoclear'],
    'butorphanol': ['butorphanol', 'torbugesic', 'stadol'],
    'hydromorphone': ['hydromorphone', 'dilaudid'],
    'methadone': ['methadone', 'physeptone'],
    'tramadol': ['tramadol', 'ultram'],
    'fentanyl': ['fentanyl', 'duragesic'],
    'ondansetron': ['ondansetron', 'zofran'],
    'maropitant_injectable': [],  # handled under maropitant
    'cerenia_injectable': [],     # handled under maropitant
    'enrofloxacin': ['enrofloxacin', 'baytril', 'enrocare', 'enrotab'],
    'amoxicillin': ['amoxicillin', 'clavamox', 'augmentin'],
    'amoxicillin_clavulanate': ['clavamox', 'augmentin', 'amoxiclav'],
    'doxycycline': ['doxycycline', 'vibramycin'],
    'metronidazole': ['metronidazole', 'flagyl'],
    'clindamycin': ['clindamycin', 'antirobe'],
    'trimethoprim_sulfa': ['trimethoprim', 'sulfamethoxazole', 'tmp-smz', 'bactrim', 'di-trim'],
    'azithromycin': ['azithromycin', 'zithromax'],
    'chloramphenicol': ['chloramphenicol', 'chloromycetin'],
    'marbofloxacin': ['marbofloxacin', 'zeniquin'],
    'pradofloxacin': ['pradofloxacin', 'veraflox'],
    'furosemide': ['furosemide', 'lasix', 'salix'],
    'enalapril': ['enalapril', 'enacard', 'vasotec'],
    'benazepril': ['benazepril', 'fortekor', 'lotensin'],
    'pimobendan': ['pimobendan', 'vetmedin'],
    'atenolol': ['atenolol', 'tenormin'],
    'amlodipine': ['amlodipine', 'norvasc'],
    'digoxin': ['digoxin', 'lanoxin'],
    'spironolactone': ['spironolactone', 'aldactone'],
    'prednisone': ['prednisone', 'prednisolone', 'deltasone'],
    'prednisolone': ['prednisolone', 'omnipred', 'pediapred'],
    'dexamethasone': ['dexamethasone', 'azium'],
    'methylprednisolone': ['methylprednisolone', 'depo-medrol', 'medrol'],
    'triamcinolone': ['triamcinolone', 'vetalog', 'kenalog'],
    'cytopoint': ['cytopoint', 'lokivetmab'],
    'apoquel': ['apoquel', 'oclacitinib'],
    'cyclosporine': ['cyclosporine', 'atopica', 'optimmune'],
    'hydroxyzine': ['hydroxyzine', 'atarax'],
    'diphenhydramine': ['diphenhydramine', 'benadryl'],
    'cerenia_chewable': [],  # handled under maropitant
    'phenobarbital': ['phenobarbital', 'luminal'],
    'potassium_bromide': ['potassium bromide', 'k-bro-vet'],
    'levetiracetam': ['levetiracetam', 'keppra'],
    'zonisamide': ['zonisamide', 'zonegran'],
    'omeprazole': ['omeprazole', 'prilosec', 'gastrogard'],
    'famotidine': ['famotidine', 'pepcid'],
    'sucralfate': ['sucralfate', 'carafate'],
    'metoclopramide': ['metoclopramide', 'reglan'],
    'maropitant_anti_emetic': [],  # handled under maropitant
    'lactulose': ['lactulose', 'enulose'],
    'cisapride': ['cisapride', 'propulsid'],
    'methimazole': ['methimazole', 'felimazole', 'tapazole'],
    'levothyroxine': ['levothyroxine', 'soloxine', 'thyro-tabs'],
    'trilostane': ['trilostane', 'vetoryl'],
    'mitotane': ['mitotane', 'lysodren'],
    'selegiline': ['selegiline', 'anipryl', 'eldepryl'],
    'insulin': ['insulin', 'vetsulin', 'caninsulin', 'glargine', 'lantus'],
    'glipizide': ['glipizide', 'glucotrol'],
    'acarbose': ['acarbose', 'precose'],
    'albendazole': ['albendazole', 'valbazen'],
    'fenbendazole': ['fenbendazole', 'panacur', 'safe-guard'],
    'pyrantel': ['pyrantel', 'strongid'],
    'praziquantel': ['praziquantel', 'droncit', 'drontal'],
    'selamectin': ['selamectin', 'revolution', 'stronghold'],
    'milbemycin': ['milbemycin', 'interceptor'],
    'ivermectin': ['ivermectin', 'heartgard', 'ivomec'],
    'spinosad': ['spinosad', 'comfortis'],
    'afoxolaner': ['afoxolaner', 'nexgard'],
    'fluralaner': ['fluralaner', 'bravecto'],
    'sarolaner': ['sarolaner', 'simparica'],
    'isoxapropyl': ['lotilaner', 'credelio'],
    'fipronil': ['fipronil', 'frontline'],
    'imidacloprid': ['imidacloprid', 'advantage'],
    'nitenpyram': ['nitenpyram', 'capstar'],
}

# Clean up empty placeholder groups
DRUG_GROUPS = {k: v for k, v in DRUG_GROUPS.items() if v}

def fetch_products():
    url = f'{SUPA_URL}/rest/v1/products?select=id,name,dispensing_unit,qty_min,qty_max&order=name&limit=2000'
    req = urllib.request.Request(url, headers={
        'apikey': SUPA_KEY,
        'Authorization': f'Bearer {SUPA_KEY}',
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def find_group(product_name):
    """Return the canonical drug name if this product matches a known group."""
    name_lower = product_name.lower()
    for canonical, aliases in DRUG_GROUPS.items():
        for alias in aliases:
            if alias in name_lower:
                return canonical
    return None

def main():
    print('Fetching products from Supabase...')
    products = fetch_products()
    print(f'  {len(products)} products loaded\n')

    # Group products by drug
    groups = {}
    unmatched = []
    for p in products:
        group = find_group(p['name'])
        if group:
            groups.setdefault(group, []).append(p)
        # Only track unmatched if they have qty_min (are being tracked)
        elif p['qty_min'] is not None:
            unmatched.append(p)

    # Report
    print('=' * 70)
    print('DRUG EQUIVALENCE GROUPS')
    print('=' * 70)

    rows = []
    issues = []

    for canonical, prods in sorted(groups.items()):
        if len(prods) < 2:
            continue  # Only report actual duplicates

        mins = [p['qty_min'] for p in prods if p['qty_min'] is not None]
        maxs = [p['qty_max'] for p in prods if p['qty_max'] is not None]
        min_mismatch = len(set(mins)) > 1
        max_mismatch = len(set(maxs)) > 1
        has_nulls    = any(p['qty_min'] is None for p in prods)
        flag = ''
        if min_mismatch or max_mismatch:
            flag = '⚠  MIN/MAX MISMATCH'
        elif has_nulls:
            flag = '⚠  SOME NOT TRACKED'

        print(f'\n[{canonical.upper().replace("_", " ")}]  {flag}')
        for p in prods:
            tracked = '✓' if p['qty_min'] is not None else '○'
            print(f'  {tracked} {p["name"]}')
            print(f'      qty_min={p["qty_min"]}  qty_max={p["qty_max"]}  unit={p["dispensing_unit"]}')
            rows.append({
                'drug_group': canonical,
                'product_name': p['name'],
                'dispensing_unit': p['dispensing_unit'],
                'qty_min': p['qty_min'],
                'qty_max': p['qty_max'],
                'tracked': 'yes' if p['qty_min'] is not None else 'no',
                'issue': flag,
            })
            if flag:
                issues.append(p['name'])

    print('\n' + '=' * 70)
    print(f'TRACKED PRODUCTS WITH NO KNOWN EQUIVALENT ({len(unmatched)})')
    print('=' * 70)
    for p in unmatched:
        print(f'  {p["name"]}  (min={p["qty_min"]} max={p["qty_max"]})')

    # Save CSV
    out_path = '/Users/meganhenley/Downloads/medsync_deploy/audit_drug_equivalents.csv'
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['drug_group','product_name','dispensing_unit','qty_min','qty_max','tracked','issue'])
        writer.writeheader()
        writer.writerows(rows)

    print(f'\n✓ Report saved to: {out_path}')
    print(f'\nSummary: {len(groups)} drug groups found | {sum(1 for g in groups.values() if len(g) > 1)} with duplicates | {len(issues)} products with mismatched or missing min/max')

if __name__ == '__main__':
    main()
