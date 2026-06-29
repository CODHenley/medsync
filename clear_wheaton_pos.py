#!/usr/bin/env python3
"""
Clear all po_items for Wheaton from Supabase.
Goods lost data is untouched.

Usage (dry run):
  python3 clear_wheaton_pos.py

Apply:
  SUPA_SERVICE_KEY="sb_secret_..." python3 clear_wheaton_pos.py --apply
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

SUPA_URL        = "https://aemkdummdrmxtwrkggjw.supabase.co"
WHEATON_UUID    = "11111111-0000-0000-0000-000000000004"

def supa_get(key, path):
    req = urllib.request.Request(
        SUPA_URL + path,
        headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def supa_delete(key, path):
    req = urllib.request.Request(
        SUPA_URL + path,
        headers={
            "apikey":        key,
            "Authorization": f"Bearer {key}",
            "Prefer":        "return=minimal",
        }
    )
    req.get_method = lambda: "DELETE"
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Delete rows (default: dry run)")
    args = ap.parse_args()

    service_key = os.environ.get("SUPA_SERVICE_KEY", "").strip()
    if args.apply and not service_key:
        sys.exit("ERROR: Set SUPA_SERVICE_KEY env var to apply changes.")

    anon_key = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0"
        ".JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
    )
    read_key = service_key or anon_key

    print("Counting po_items for Wheaton …")
    rows = supa_get(read_key, f"/rest/v1/po_items?select=id,product_name,week_start,status&location_id=eq.{WHEATON_UUID}&limit=5000")
    if isinstance(rows, dict) and "message" in rows:
        sys.exit(f"Supabase error: {rows}")

    print(f"  Found {len(rows)} po_items rows for Wheaton\n")
    if not rows:
        print("Nothing to delete.")
        return

    # Show a sample
    print("Sample rows to be deleted:")
    for r in rows[:10]:
        print(f"  {r.get('week_start','?'):12s}  {r.get('status','?'):12s}  {r.get('product_name','?')}")
    if len(rows) > 10:
        print(f"  … and {len(rows)-10} more\n")

    if not args.apply:
        print(f"\nDRY RUN — {len(rows)} rows would be deleted.")
        print("Pass --apply with SUPA_SERVICE_KEY set to delete.")
        return

    print(f"\nDeleting all {len(rows)} Wheaton po_items …")
    status = supa_delete(service_key, f"/rest/v1/po_items?location_id=eq.{WHEATON_UUID}")
    if status in (200, 204):
        print(f"  ✓ Done — all Wheaton po_items cleared (HTTP {status})")
    else:
        print(f"  ✗ HTTP {status} — delete may have failed, check Supabase")

if __name__ == "__main__":
    main()
