#!/usr/bin/env python3
"""
MedSync SKU Backfill
--------------------
Cross-references MedSync products against an inventory workbook and patches
any products missing an NDC/SKU.

Supports two workbook formats (auto-detected by sheet names):
  • Q2 WH Inventory Count workbook (multiple pharmacy/vaccine sheets)
  • MedSync De Novo Loading Order (single sheet, col B=name, col C=SKU)

Usage (dry run — shows what would change, no writes):
  python3 sku_backfill.py --xlsx MedSync_DeNovo_Loading_Order_v1.xlsx

Apply changes:
  SUPA_SERVICE_KEY="sb_secret_..." python3 sku_backfill.py --xlsx MedSync_DeNovo_Loading_Order_v1.xlsx --apply
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error

try:
    import openpyxl
except ImportError:
    sys.exit("pip install openpyxl  then re-run")

# ── Config ─────────────────────────────────────────────────────────────────
SUPA_URL  = "https://aemkdummdrmxtwrkggjw.supabase.co"
ANON_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# Sheets and which columns hold (item_name, product_code). All 0-indexed.
SHEET_COLS = {
    "Pharmacy - General ":      (0, 2),
    "Pharmacy - Ocular ":       (0, 1),
    "Pharmacy - Preventatives ":(0, 1),
    "Pharmacy - Skin":          (0, 1),
    "Vaccines ":                (0, 1),
    "IDEXX Labs ":              (0, 1),
    "IDEXX Consumables ":       (0, 1),
    "Diets":                    (0, 1),
    "Hospital Inventory":       (0, 4),
    "Stable Hospital Inventory":(0, 3),
}

# ── Helpers ─────────────────────────────────────────────────────────────────
def _norm(s):
    """Lowercase, collapse whitespace, strip punctuation for fuzzy matching."""
    s = str(s or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sku_str(val):
    if val is None:
        return None
    if isinstance(val, float):
        return str(int(val)) if val == int(val) else str(val)
    return str(val).strip()


DENOVO_SHEET = "De Novo Loading Order"

def _is_real_sku(s):
    """Return True if s looks like an actual SKU/catalog code, not a brand/model name."""
    if not s or len(s) < 4:
        return False
    # Model names have spaces; actual codes do not
    if " " in s:
        return False
    return True


def load_spreadsheet(path):
    """Return dict: normalised_name → (sku, original_name, sheet).

    Auto-detects workbook format:
      - If workbook contains SHEET_COLS keys → Q2 inventory format (multiple sheets)
      - If workbook contains De Novo Loading Order sheet → de novo format (single sheet)
    """
    wb = openpyxl.load_workbook(path)
    mapping = {}

    if DENOVO_SHEET in wb.sheetnames:
        # De Novo Loading Order format: col B (index 1) = name, col C (index 2) = SKU
        ws = wb[DENOVO_SHEET]
        for row in ws.iter_rows(min_row=5, values_only=True):
            row_num = row[0]
            name    = row[1]
            sku_raw = row[2]
            if not name or not isinstance(row_num, int):
                continue
            sku_s = _sku_str(sku_raw)
            if not sku_s or not _is_real_sku(sku_s):
                continue
            key = _norm(name)
            if key and key not in ("medication", "item", "vaccine", "supplies"):
                mapping[key] = (sku_s, str(name).strip(), DENOVO_SHEET)
    else:
        # Q2 WH Inventory Count format: multiple named sheets
        for sheet, (icol, scol) in SHEET_COLS.items():
            if sheet not in wb.sheetnames:
                continue
            ws = wb[sheet]
            for row in ws.iter_rows(min_row=2, values_only=True):
                name = row[icol]
                sku  = row[scol]
                if not name or not sku:
                    continue
                sku_s = _sku_str(sku)
                if not sku_s:
                    continue
                key = _norm(name)
                if key and key not in ("medication", "item", "vaccine", "supplies"):
                    mapping[key] = (sku_s, str(name).strip(), sheet.strip())

    return mapping


def supa_get(key, path):
    req = urllib.request.Request(
        SUPA_URL + path,
        headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# Manual overrides: exact MedSync product name → correct SKU
# Use this to fix fuzzy-match errors or products not in the spreadsheet.
MANUAL_OVERRIDES = {
    "vanguard bordetella vaccine oral sf":      "10014057",  # Zoetis — not in workbook
    "vanguard rabies vaccine - 1 year":         "10016542",  # 1-year, not 3-year
    "purevax feline rabies vaccine - 1 year":   "159730",    # Boehringer Ingelheim 1-year rabies
    "purevax feline rabies vaccine - 3 year":   "159732",    # Boehringer Ingelheim 3-year rabies
}


def supa_patch(key, path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        SUPA_URL + path,
        data=body,
        headers={
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
            "Prefer":        "return=minimal",
        }
    )
    req.get_method = lambda: "PATCH"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="Path to inventory workbook")
    ap.add_argument("--apply", action="store_true", help="Write changes to Supabase (default: dry run)")
    args = ap.parse_args()

    service_key = os.environ.get("SUPA_SERVICE_KEY", "").strip()
    if args.apply and not service_key:
        sys.exit("ERROR: Set SUPA_SERVICE_KEY env var to apply changes.")

    read_key = service_key or ANON_KEY

    print("Loading spreadsheet …")
    sheet_map = load_spreadsheet(args.xlsx)
    print(f"  {len(sheet_map)} products with SKUs in workbook")

    print("\nFetching all products missing SKU from Supabase …")
    all_products = []
    page_size = 1000
    offset = 0
    while True:
        batch = supa_get(
            read_key,
            f"/rest/v1/products?select=id,name,ndc&limit={page_size}&offset={offset}"
        )
        if isinstance(batch, dict) and "message" in batch:
            sys.exit(f"Supabase error: {batch}")
        all_products.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    total_products = len(all_products)
    missing_sku = [p for p in all_products if not (p.get("ndc") or "").strip()]
    print(f"  {total_products} total products, {len(missing_sku)} missing SKU")

    def find_in_sheet(name):
        key = _norm(name)
        if key in MANUAL_OVERRIDES:
            return (MANUAL_OVERRIDES[key], name + " [manual override]", "overrides")
        match = sheet_map.get(key)
        if not match:
            words = key.split()
            for skey, val in sheet_map.items():
                swords = skey.split()
                common = sum(1 for w in words[:4] if w in swords)
                if common >= 3:
                    match = val
                    break
        return match

    product_patches = {}   # product_id → {ndc, product_name, matched_name, sheet}
    no_match        = []

    for prod in missing_sku:
        prod_id   = prod["id"]
        prod_name = prod["name"] or ""
        match = find_in_sheet(prod_name)
        if match:
            sku, matched_name, sheet = match
            product_patches[prod_id] = {
                "ndc": sku,
                "product_name": prod_name,
                "matched_name": matched_name,
                "sheet": sheet,
            }
        else:
            no_match.append((prod_id, prod_name, "not found in workbook"))

    # ── Report ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"Products to update (add SKU):      {len(product_patches)}")
    print(f"No match found (manual review):    {len(no_match)}")
    print(f"{'='*70}\n")

    if product_patches:
        print("WILL ADD SKU TO EXISTING PRODUCT:")
        for pid, info in product_patches.items():
            print(f"  {info['product_name']!r:60s} → {info['ndc']:12s}  [{info['sheet']}]")
        print()

    if no_match:
        print("NO MATCH (manual review needed):")
        for prod_id, name, reason in no_match:
            print(f"  {name!r:60s}  [{reason}]")
        print()

    if not args.apply:
        print("DRY RUN — pass --apply with SUPA_SERVICE_KEY set to write changes.")
        return

    # ── Apply ─────────────────────────────────────────────────────────────────
    print("Applying patches …")
    ok = err = 0

    for pid, info in product_patches.items():
        status = supa_patch(service_key, f"/rest/v1/products?id=eq.{pid}", {"ndc": info["ndc"]})
        if status in (200, 204):
            print(f"  ✓ {info['product_name']} → {info['ndc']}")
            ok += 1
        else:
            print(f"  ✗ {info['product_name']} → HTTP {status}")
            err += 1

    print(f"\nDone: {ok} updated, {err} errors.")


if __name__ == "__main__":
    main()
