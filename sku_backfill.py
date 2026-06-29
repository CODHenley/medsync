#!/usr/bin/env python3
"""
MedSync SKU Backfill
--------------------
Cross-references active lots against the Q2 inventory workbook and patches
any products missing an NDC/SKU.

Usage (dry run — shows what would change, no writes):
  python3 sku_backfill.py --xlsx Q2__WH_Inventory_Count_2026.xlsx

Apply changes:
  SUPA_SERVICE_KEY="sb_secret_..." python3 sku_backfill.py --xlsx Q2__WH_Inventory_Count_2026.xlsx --apply
"""

import argparse
import json
import os
import re
import sys
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


def load_spreadsheet(path):
    """Return dict: normalised_name → (sku, original_name, sheet)."""
    wb = openpyxl.load_workbook(path)
    mapping = {}
    for sheet, (icol, scol) in SHEET_COLS.items():
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
            if key and key not in ("medication","item","vaccine","supplies"):
                mapping[key] = (sku_s, str(name).strip(), sheet.strip())
    return mapping


def supa_get(key, path):
    req = urllib.request.Request(
        SUPA_URL + path,
        headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


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

    # Location UUIDs — must match what the browser sends so RLS passes
    LOC_UUIDS = [
        "11111111-0000-0000-0000-000000000001",  # Lincoln Park
        "11111111-0000-0000-0000-000000000002",  # Old Orchard
        "11111111-0000-0000-0000-000000000003",  # West Loop
        "11111111-0000-0000-0000-000000000004",  # Wheaton
    ]
    loc_in = "(" + ",".join(LOC_UUIDS) + ")"

    print("\nFetching all lots + products from Supabase …")
    rows = supa_get(
        read_key,
        "/rest/v1/lots?select=id,lot_number,notes,status,products(id,name,ndc)"
        f"&location_id=in.{loc_in}"
        "&limit=1000"
    )
    if isinstance(rows, dict) and "message" in rows:
        sys.exit(f"Supabase error: {rows}")

    print(f"  {len(rows)} lots returned")

    # Group by product so we patch each product once
    product_patches = {}   # product_id → {ndc, product_name, lot_numbers[]}
    no_match = []

    for lot in rows:
        prod = lot.get("products") or {}
        prod_id   = prod.get("id")
        prod_name = prod.get("name") or (lot.get("notes") or "").replace("Vetspire inventory:", "").strip()
        existing_ndc = prod.get("ndc") or ""

        if not prod_id:
            no_match.append((lot["lot_number"], prod_name, "no product record"))
            continue

        if existing_ndc.strip():
            continue  # already has SKU

        # Try exact normalised match
        key = _norm(prod_name)
        match = sheet_map.get(key)

        # Fallback: strip dosage/size suffixes and try a word-overlap match
        if not match:
            words = key.split()
            for skey, (ssku, sname, ssheet) in sheet_map.items():
                swords = skey.split()
                common = sum(1 for w in words[:4] if w in swords)
                if common >= 3:
                    match = (ssku, sname, ssheet)
                    break

        if match:
            sku, matched_name, sheet = match
            if prod_id not in product_patches:
                product_patches[prod_id] = {"ndc": sku, "product_name": prod_name,
                                             "matched_name": matched_name,
                                             "sheet": sheet, "lots": []}
            product_patches[prod_id]["lots"].append(lot["lot_number"])
        else:
            no_match.append((lot["lot_number"], prod_name, "not found in workbook"))

    # ── Report ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"Products to update: {len(product_patches)}")
    print(f"No match found:     {len(no_match)}")
    print(f"{'='*70}\n")

    if product_patches:
        print("WILL UPDATE:")
        for pid, info in product_patches.items():
            print(f"  product {pid}")
            print(f"    MedSync name : {info['product_name']}")
            print(f"    Matched to   : {info['matched_name']}  [{info['sheet']}]")
            print(f"    SKU to set   : {info['ndc']}")
            print(f"    Lots         : {', '.join(info['lots'])}")
            print()

    if no_match:
        print("NO MATCH (manual review needed):")
        for lot_num, name, reason in no_match:
            print(f"  LOT {lot_num:10s}  {name!r:50s}  [{reason}]")
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
