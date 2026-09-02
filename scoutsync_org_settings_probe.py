#!/usr/bin/env python3
"""
One-off: check organization_settings.settings_json.cogs_min/cogs_max and
location_settings.cogs_pct before building the ScoutSync Budget vs Spend
report, so its budget formula (revenue x cogs target %) uses whatever
target Scout is actually operating against today instead of a guessed
default.
"""
import json, urllib.request, urllib.error

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"


def supa_get(path, params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?{qs}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code} on {path}: {e.read().decode()[:300]}")
        return None


def main():
    print("=== organization_settings ===")
    print(json.dumps(supa_get("organization_settings", {"select": "*"}), indent=2))

    print("\n=== location_settings ===")
    print(json.dumps(supa_get("location_settings", {"select": "*"}), indent=2))

    print("\n=== purchase_history: distinct sources + row count per location ===")
    rows = supa_get("purchase_history", {"select": "location_id,source,amount,purchased_at", "order": "purchased_at.desc", "limit": "2000"})
    if rows:
        by_loc_source = {}
        for r in rows:
            key = (r["location_id"], r["source"])
            by_loc_source[key] = by_loc_source.get(key, 0) + 1
        for (loc, src), count in sorted(by_loc_source.items()):
            print(f"  {loc} / {src}: {count} rows")
        print(f"  total rows fetched (capped at 2000): {len(rows)}")
        print(f"  most recent purchased_at: {rows[0]['purchased_at']}")
        print(f"  oldest in this page: {rows[-1]['purchased_at']}")


if __name__ == "__main__":
    main()
