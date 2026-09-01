#!/usr/bin/env python3
"""
One-off: Wheaton is flagged "Scheduled, $0 revenue" for Tue Aug 4, 2026 on
the Days Closed report. User is looking at Vetspire directly and seeing
real appointments/cancellations that day, which the $0-revenue flag alone
can't speak to (it's purely provider_shifts vs. v_avg_transaction_charge_daily
-- it says nothing about appointments or cancellations).

Pulls everything ScoutSync has synced for Wheaton on that one date across
all four relevant tables, to see what's actually there:
  - provider_shifts       (why it's "scheduled")
  - v_avg_transaction_charge_daily (why it's "$0 revenue")
  - appointment_events    (real appointment/cancellation activity that day,
                            synced fresh in vetspire_appointment_events_sync.py)
  - invoice_line_items    (raw rows behind the revenue view, in case the
                            view is aggregating something unexpected)
"""
import json, os, urllib.request, urllib.error

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"
WHEATON = "11111111-0000-0000-0000-000000000004"
DATE = "2026-08-04"


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
    print(f"=== provider_shifts, Wheaton, {DATE} ===")
    rows = supa_get("provider_shifts", {
        "location_id": f"eq.{WHEATON}",
        "shift_start": f"lte.{DATE}",
        "shift_end": f"gte.{DATE}",
        "select": "shift_start,shift_end,provider_id,vetspire_shift_id",
    })
    print(json.dumps(rows, indent=2))

    print(f"\n=== v_avg_transaction_charge_daily, Wheaton, {DATE} ===")
    rows = supa_get("v_avg_transaction_charge_daily", {
        "location_id": f"eq.{WHEATON}",
        "service_date": f"eq.{DATE}",
        "select": "*",
    })
    print(json.dumps(rows, indent=2))

    print(f"\n=== invoice_line_items, Wheaton, {DATE} (raw rows behind the view) ===")
    rows = supa_get("invoice_line_items", {
        "location_id": f"eq.{WHEATON}",
        "service_date": f"eq.{DATE}",
        "select": "*",
        "limit": "50",
    })
    print(json.dumps(rows, indent=2))

    print(f"\n=== invoice_line_items, Wheaton, Jul 28 - Aug 11 2026 (wider window -- checking for a nearby billing-date mismatch) ===")
    rows = supa_get("invoice_line_items", {
        "location_id": f"eq.{WHEATON}",
        "service_date": "gte.2026-07-28",
        "and": "(service_date.lte.2026-08-11)",
        "select": "service_date,vetspire_invoice_id,provider_id,category,description,amount",
        "order": "service_date.asc",
        "limit": "100",
    })
    print(json.dumps(rows, indent=2))
    if rows:
        by_date = {}
        for r in rows:
            by_date[r["service_date"]] = by_date.get(r["service_date"], 0) + float(r.get("amount") or 0)
        print(f"  -> revenue by date: {by_date}")

    print(f"\n=== appointment_events, Wheaton, {DATE} ===")
    rows = supa_get("appointment_events", {
        "location_id": f"eq.{WHEATON}",
        "scheduled_start": f"gte.{DATE}T00:00:00",
        "and": f"(scheduled_start.lt.{DATE}T23:59:59)",
        "select": "vetspire_appointment_id,provider_id,appointment_type,scheduled_start,status,deleted,deletion_reason,duration_minutes",
        "limit": "200",
    })
    print(json.dumps(rows, indent=2))
    if rows:
        print(f"\n  -> {len(rows)} appointment_events rows for Wheaton on {DATE}")
        statuses = {}
        for r in rows:
            statuses[r.get("status")] = statuses.get(r.get("status"), 0) + 1
        print(f"  -> status breakdown: {statuses}")
        print(f"  -> deleted count: {sum(1 for r in rows if r.get('deleted'))}")


if __name__ == "__main__":
    main()
