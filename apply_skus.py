#!/usr/bin/env python3
"""
apply_skus.py
Applies SKUs from the returned spreadsheet and removes discontinued products.
"""
import json, urllib.request, urllib.parse, os, sys

os.environ.pop('https_proxy', None); os.environ.pop('HTTPS_PROXY', None)

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
H = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

def supa(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(SUPA_URL + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print(f"    ERROR {e.code}: {e.read().decode()}")
        raise

# ── Products with confirmed SKUs ──────────────────────────────────────────────
SKUS = [
    ("Elura",                    "CA554515HAM"),
    ("Mannitol 20%",             "VEDC211"),
    ("Ofloxacin",                "60505056000"),
    ("Pimobendan",               "103184"),
    ("Royal Canin Feline SO",    "60434"),
]

# ── Products no longer carried — remove from products table ───────────────────
DISCONTINUED = [
    "Acepromazine Inj 10 mg/ml",
    "Azithromycin 200 mg/5 ml Sus (30 ml bottle)",
    "Azithromycin 250 mg tablets",
    "Enrofloxacin Inj 22.7 mg/ml",
    "Famotidine 20 mg tablets",
    "Gabapentin Solu 50 mg/ml",
    "Hill's Onc Feline 2.9 oz",
    "Marbofloxacin 25 mg tablets",
    "Marbofloxacin 100 mg tablets",
    "Maropitant 160 mg tablets",
    "Mirtazapine 7.5 mg tablets",
    "Nitro-Bid Ointment 2%",
    "Oxytocin Inj 20 USP units/ml",
    "Zenalpha 0.5 mg/ml",
    "Clevor Opth Solu",
]

print("=== Applying SKUs ===")
for name_fragment, sku in SKUS:
    enc = urllib.parse.quote(name_fragment, safe='')
    status = supa("PATCH", f"/rest/v1/products?name=ilike.*{enc}*", {"sku": sku})
    print(f"  ✓ {name_fragment:<35} SKU: {sku}  (HTTP {status})")

print("\n=== Removing discontinued products ===")
for name in DISCONTINUED:
    enc = urllib.parse.quote(name, safe='')
    status = supa("DELETE", f"/rest/v1/products?name=eq.{enc}")
    print(f"  ✗ removed: {name}  (HTTP {status})")

print("\nDone.")
