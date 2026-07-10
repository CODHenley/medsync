#!/usr/bin/env python3
"""
MedSync — UPC/Barcode Lookup for Physical Count Scanning
----------------------------------------------------------
Queries the FDA OpenFDA NDC API to find UPC-A barcodes for products
in the MedSync products table. Updates products.ndc with the barcode-
encoded NDC so cycle count scanning works by scanning the physical box.

Run from the medsync repo root:
    python3 upc_lookup.py [--dry-run] [--limit N]

Output:
    upc_lookup_results.csv  — full results (found, not-found, skipped)
    upc_lookup_updates.sql  — SQL UPDATE statements for review before running

Auth: Uses the public anon key (read) + service role key for writes.
Set SUPABASE_SERVICE_ROLE_KEY env var, or pass --dry-run to skip writes.
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import argparse
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SUPA_URL  = "https://aemkdummdrmxtwrkggjw.supabase.co"
ANON_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
FDA_URL   = "https://api.fda.gov/drug/ndc.json"
UPC_DB    = "https://api.upcitemdb.com/prod/trial/lookup"  # free tier: 100/day

RATE_LIMIT_DELAY = 0.25  # seconds between FDA API calls


# ── HTTP helpers ─────────────────────────────────────────────────────────────
def http_get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def http_patch(url, data, headers):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print(f"    PATCH error {e.code}: {e.read().decode()[:200]}")
        return e.code


# ── Supabase ─────────────────────────────────────────────────────────────────
def fetch_products():
    """Fetch all products with name, ndc, sku, vetspire_product_id."""
    all_rows, page, page_size = [], 0, 1000
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    while True:
        url = (f"{SUPA_URL}/rest/v1/products"
               f"?select=id,name,ndc,sku,vetspire_product_id"
               f"&order=name.asc&limit={page_size}&offset={page * page_size}")
        status, data = http_get(url, headers)
        if status != 200:
            print(f"ERROR fetching products: HTTP {status}")
            sys.exit(1)
        all_rows.extend(data)
        if len(data) < page_size:
            break
        page += 1
    return all_rows


def update_product_ndc(product_id, ndc, service_key):
    headers = {
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }
    url = f"{SUPA_URL}/rest/v1/products?id=eq.{product_id}"
    return http_patch(url, {"ndc": ndc}, headers)


# ── NDC → UPC conversion ──────────────────────────────────────────────────────
def ndc_to_upc_candidates(ndc_raw):
    """
    Drug UPC-A barcodes encode the NDC in digits 2–11 of a 12-digit barcode.
    NDCs come in several formats (5-4-2, 5-3-2, 4-4-2). We normalise to
    10 digits (zero-pad each segment) and prepend '0', then compute check digit.
    Returns list of candidate 12-digit UPC strings.
    """
    ndc = str(ndc_raw).strip().replace("-", "").replace(" ", "")
    candidates = []

    # Try the raw 10-digit NDC as barcode digits 2–11
    if len(ndc) == 10:
        candidates.append(ndc)
    # If 9 digits, try padding in different positions
    elif len(ndc) == 9:
        candidates.extend([ndc + "0", "0" + ndc])
    # If already 11 digits (some FDA records include the check digit)
    elif len(ndc) == 11:
        candidates.append(ndc[:10])

    # Build 12-digit UPC candidates (leading 0 + 10-digit NDC + check digit)
    upc_candidates = []
    for c in candidates:
        if len(c) == 10:
            raw11 = "0" + c
            check = upc_check_digit(raw11)
            upc_candidates.append(raw11 + str(check))
    return upc_candidates


def upc_check_digit(digits_11):
    """Compute UPC-A check digit from first 11 digits."""
    total = 0
    for i, d in enumerate(digits_11):
        total += int(d) * (3 if i % 2 == 1 else 1)
    return (10 - (total % 10)) % 10


def extract_ndc_from_upc(upc):
    """Reverse: extract 10-digit NDC from a 12-digit UPC-A."""
    if len(upc) == 12 and upc[0] == "0":
        return upc[1:11]
    return None


# ── FDA OpenFDA lookup ────────────────────────────────────────────────────────
def fda_lookup_by_ndc(ndc):
    """Query OpenFDA NDC endpoint by product_ndc or package_ndc."""
    ndc_clean = str(ndc).strip().replace("-", "")
    # Try formatted NDC (FDA uses hyphenated format)
    # Common formats: 12345-678-90 or 12345-6789-0
    queries = []
    if len(ndc_clean) == 10:
        queries.append(f'{ndc_clean[:5]}-{ndc_clean[5:9]}-{ndc_clean[9:]}')  # 5-4-1
        queries.append(f'{ndc_clean[:5]}-{ndc_clean[5:8]}-{ndc_clean[8:]}')  # 5-3-2
        queries.append(ndc_clean)  # raw

    for q in queries:
        url = f"{FDA_URL}?search=product_ndc:{urllib.parse.quote(q)}&limit=3"
        status, data = http_get(url)
        time.sleep(RATE_LIMIT_DELAY)
        if status == 200 and data.get("results"):
            return data["results"][0]
        # Also try package_ndc
        url2 = f"{FDA_URL}?search=packaging.package_ndc:{urllib.parse.quote(q)}&limit=3"
        status2, data2 = http_get(url2)
        time.sleep(RATE_LIMIT_DELAY)
        if status2 == 200 and data2.get("results"):
            return data2["results"][0]
    return None


def name_matches_fda(product_name, fda_result):
    """
    Validate that an FDA result is actually the right drug.
    Requires at least one meaningful word (4+ chars) from the product name
    to appear in the FDA brand or generic name.
    """
    pname = product_name.lower()
    brand   = (fda_result.get("brand_name") or "").lower()
    generic = (fda_result.get("generic_name") or "").lower()
    fda_text = brand + " " + generic

    # Extract meaningful words from product name (skip dosage/units/noise)
    skip = {"mg", "ml", "mcg", "each", "count", "tablet", "tablets", "capsule",
            "capsules", "injection", "inj", "solution", "oral", "the", "and",
            "for", "with", "size", "dose", "pack", "box", "case", "kit"}
    words = [w.strip("()[],:") for w in pname.split() if len(w) >= 4 and w not in skip]

    return any(w in fda_text for w in words[:5])


def is_drug_product(name):
    """
    Heuristic: skip obvious non-drug products (equipment, food, supplies).
    Only attempt FDA lookup for pharmaceutical products.
    """
    name_lower = name.lower()
    skip_keywords = [
        "cable", "ethernet", "printer", "syringe tip", "forceps", "clamp",
        "scissors", "scalpel", "blade", "stapler", "catheter tip", "tube adapter",
        "muzzle", "splint", "gag", "towel", "glove", "pouch", "label", "bag",
        "bottle wash", "wash bottle", "pad", "underpad", "shoe cover", "sign",
        "rod ", " rod", "stand ", "iv stand", "paper", "jar", "tray", "cup",
        "hill's", "royal canin", "purina", "science diet", "hills ",
        "diet, canine", "diet, feline", "diet feline", "diet canine",
        "food ", " food", "chow", "treat ",
        "ethernet", "canon", "printer", "assembly", "engager",
        "patch cable", "foot cable", "shielded cable",
        "autoclave pouch", "capillary tube", "centrifuge tube",
        "biohazard label", "anesthesia label", "butorphanol label",
        "specimen", "bibulous", "pipette tip", "sample cup",
        "(external rx)", "(otc)",
    ]
    return not any(kw in name_lower for kw in skip_keywords)


def extract_upc_from_fda_result(result):
    """
    FDA results include packaging info. Extract the 10-digit product_ndc
    and construct the UPC-A. Also check packaging.package_ndc entries.
    """
    found_ndcs = set()

    product_ndc = result.get("product_ndc", "")
    if product_ndc:
        found_ndcs.add(product_ndc.replace("-", ""))

    for pkg in result.get("packaging", []):
        pkg_ndc = pkg.get("package_ndc", "")
        if pkg_ndc:
            # Package NDC includes the package code — extract product portion
            parts = pkg_ndc.split("-")
            if len(parts) >= 2:
                found_ndcs.add("".join(parts[:2]).ljust(10, "0")[:10])
            found_ndcs.add(pkg_ndc.replace("-", "")[:10])

    # Return the best candidate UPC
    for ndc in found_ndcs:
        candidates = ndc_to_upc_candidates(ndc)
        if candidates:
            return candidates[0], ndc
    return None, None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Look up UPC barcodes for MedSync products")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to Supabase")
    parser.add_argument("--limit",   type=int, default=0, help="Process only first N products")
    parser.add_argument("--name",    type=str, default="", help="Filter to products matching name")
    args = parser.parse_args()

    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not service_key and not args.dry_run:
        print("ERROR: Set SUPABASE_SERVICE_ROLE_KEY env var, or use --dry-run")
        sys.exit(1)

    print(f"\n=== MedSync UPC Lookup — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    if args.dry_run:
        print("DRY RUN — no Supabase writes")

    products = fetch_products()
    print(f"Loaded {len(products)} products from Supabase")

    if args.name:
        products = [p for p in products if args.name.lower() in p["name"].lower()]
        print(f"Filtered to {len(products)} matching '{args.name}'")

    if args.limit:
        products = products[:args.limit]
        print(f"Limited to first {args.limit} products")

    results = []
    updated = skipped = not_found = errors = 0

    for i, p in enumerate(products):
        name = p["name"]
        pid  = p["id"]
        ndc  = p.get("ndc")
        sku  = p.get("sku")

        print(f"\n[{i+1}/{len(products)}] {name[:60]}")
        if ndc:
            print(f"  NDC: {ndc}")

        # Skip obvious non-drug products
        if not is_drug_product(name):
            print(f"  → SKIP (non-drug product)")
            skipped += 1
            results.append({
                "product_id": pid, "name": name, "original_ndc": ndc or "",
                "found_upc": "", "found_ndc": "", "method": "skipped",
                "fda_brand": "", "fda_generic": "", "status": "skipped",
            })
            continue

        fda_result = None
        method = ""

        # Only use NDC-based lookup — name fallback produces too many false matches
        if ndc:
            fda_result = fda_lookup_by_ndc(ndc)
            if fda_result:
                # Validate the match makes sense for this product
                if name_matches_fda(name, fda_result):
                    method = "ndc"
                else:
                    brand   = fda_result.get("brand_name", "")
                    generic = fda_result.get("generic_name", "")
                    print(f"  → NDC matched FDA '{brand or generic}' but name doesn't match — skipping")
                    fda_result = None

        if not fda_result:
            print(f"  → NOT FOUND in FDA database (vet-only or NDC mismatch)")
            not_found += 1
            results.append({
                "product_id": pid, "name": name, "original_ndc": ndc or "",
                "found_upc": "", "found_ndc": "", "method": "not_found",
                "fda_brand": "", "fda_generic": "", "status": "not_found",
            })
            continue

        upc, found_ndc = extract_upc_from_fda_result(fda_result)
        brand   = fda_result.get("brand_name", "")
        generic = fda_result.get("generic_name", "")
        print(f"  → FDA match ({method}): {brand or generic}")

        if not upc:
            print(f"  → Could not construct UPC from FDA data")
            not_found += 1
            results.append({
                "product_id": pid, "name": name, "original_ndc": ndc,
                "found_upc": "", "found_ndc": found_ndc or "", "method": method,
                "fda_brand": brand, "fda_generic": generic, "status": "no_upc",
            })
            continue

        print(f"  → UPC-A: {upc}  (NDC: {found_ndc})")

        # Extract scannable NDC from UPC (digits 2–11)
        scan_ndc = extract_ndc_from_upc(upc)

        # Update Supabase if NDC differs or wasn't set
        if scan_ndc and (ndc != scan_ndc):
            if not args.dry_run:
                status = update_product_ndc(pid, scan_ndc, service_key)
                if status in (200, 204):
                    print(f"  ✓ Updated products.ndc → {scan_ndc}")
                    updated += 1
                else:
                    print(f"  ✗ Supabase update failed (HTTP {status})")
                    errors += 1
            else:
                print(f"  [dry-run] Would update products.ndc → {scan_ndc}")
                updated += 1
        else:
            print(f"  NDC already correct, skipping update")
            skipped += 1

        results.append({
            "product_id": pid, "name": name, "original_ndc": ndc or "",
            "found_upc": upc, "found_ndc": found_ndc or "", "method": method,
            "fda_brand": brand, "fda_generic": generic,
            "status": "updated" if (scan_ndc and ndc != scan_ndc) else "ok",
        })

    # ── Write CSV report ─────────────────────────────────────────────────────
    csv_path = "upc_lookup_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "status", "name", "original_ndc", "found_upc", "found_ndc",
            "method", "fda_brand", "fda_generic", "product_id",
        ])
        writer.writeheader()
        writer.writerows(results)

    # ── Write SQL for manual review ──────────────────────────────────────────
    sql_path = "upc_lookup_updates.sql"
    with open(sql_path, "w") as f:
        f.write("-- MedSync UPC Lookup — generated updates\n")
        f.write(f"-- Run: {datetime.now().isoformat()}\n\n")
        for r in results:
            if r["status"] in ("updated",) and r["found_ndc"]:
                scan = extract_ndc_from_upc(r["found_upc"]) or r["found_ndc"]
                f.write(f"-- {r['name'][:70]}\n")
                f.write(f"UPDATE products SET ndc = '{scan}' WHERE id = '{r['product_id']}';\n\n")

    print(f"\n=== Summary ===")
    print(f"  Updated : {updated}")
    print(f"  Skipped : {skipped} (already correct)")
    print(f"  Not found: {not_found} (vet-only or no FDA record)")
    print(f"  Errors  : {errors}")
    print(f"\n  Report  : {csv_path}")
    print(f"  SQL     : {sql_path}")
    print(f"\nReview {sql_path} before running in Supabase if using --dry-run.")


if __name__ == "__main__":
    main()
