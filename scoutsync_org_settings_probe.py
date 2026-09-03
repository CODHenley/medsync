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

    print("\n=== purchase_history: distinct sources + row count + date range + $ per location ===")
    rows = supa_get("purchase_history", {"select": "location_id,source,amount,purchased_at", "order": "purchased_at.desc", "limit": "2000"})
    if rows:
        by_loc_source = {}
        for r in rows:
            key = (r["location_id"], r["source"])
            stats = by_loc_source.setdefault(key, {"count": 0, "total": 0.0, "min_date": r["purchased_at"], "max_date": r["purchased_at"]})
            stats["count"] += 1
            stats["total"] += float(r["amount"] or 0)
            stats["min_date"] = min(stats["min_date"], r["purchased_at"])
            stats["max_date"] = max(stats["max_date"], r["purchased_at"])
        for (loc, src), s in sorted(by_loc_source.items()):
            print(f"  {loc} / {src}: {s['count']} rows, ${s['total']:.2f} total, {s['min_date']} .. {s['max_date']}")
        print(f"  total rows fetched (capped at 2000): {len(rows)}")

        # Check for same-week overlap between vetcove_import and vetcove_weekly
        # for one location -- if both sources have rows in the same week, summing
        # both would double-count the same real-world spend.
        lp = "11111111-0000-0000-0000-000000000001"
        lp_rows = [r for r in rows if r["location_id"] == lp]
        weekly_dates = sorted(r["purchased_at"] for r in lp_rows if r["source"] == "vetcove_weekly")
        import_dates = sorted(r["purchased_at"] for r in lp_rows if r["source"] == "vetcove_import")
        print(f"\n  Lincoln Park vetcove_weekly dates: {weekly_dates[:5]} ... {weekly_dates[-5:] if len(weekly_dates) > 5 else ''}")
        print(f"  Lincoln Park vetcove_import dates (first/last 10): {import_dates[:10]} ... {import_dates[-10:]}")


if __name__ == "__main__":
    main()
