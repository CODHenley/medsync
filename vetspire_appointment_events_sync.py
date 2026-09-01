#!/usr/bin/env python3
"""
vetspire_appointment_events_sync.py
Syncs Vetspire appointments (any status -- COMPLETED, CANCELLED, NOSHOW,
PLANNED, etc.) into ScoutSync's appointment_events table, excluding
blockoff-typed rows (Lunch, Booking Appointment, etc. -- confirmed via
vetspire_cancellations_blockoff_probe.py to be routine internal placeholders,
not real client appointments or closures).

Backs two things:
- A standalone Cancellations & Deletions operations report (status IN
  ('CANCELLED', 'NOSHOW') OR deleted = true)
- A "high cancellation rate" partial-closure flag on the Days Closed report
  (cancelled+noshow+deleted / total appointments, per provider per day)

Confirmed live against production that Vetspire's DateTime scalar (used by
appointments()'s start/end args) needs a timezone-qualified ISO string
(trailing Z), unlike the NaiveDateTime/Date scalars the other syncs use.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_appointment_events_sync.py
"""
import json, os, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

# vetspire_id -> (Supabase locations.id, name) -- same 4 locations as every other sync.
LOCATIONS = {
    "23083": ("11111111-0000-0000-0000-000000000001", "Lincoln Park"),
    "27390": ("11111111-0000-0000-0000-000000000002", "Old Orchard"),
    "24356": ("11111111-0000-0000-0000-000000000003", "West Loop"),
    "28253": ("11111111-0000-0000-0000-000000000004", "Wheaton"),
}

# Same floor as vetspire_provider_shifts_sync.py -- safely before any
# location's real opening date; a location simply returns nothing before it
# existed.
SWEEP_FLOOR = "2020-01-01"
CHUNK_DAYS = int(os.environ.get("CHUNK_DAYS", "60"))
PAGE_LIMIT = 200  # appointments() has no offset param confirmed working the same way encounters() does -- keep chunks narrow instead of paginating within one

APPOINTMENTS_QUERY = """
query($locationId: ID, $start: DateTime, $end: DateTime, $limit: Int, $offset: Int) {
  appointments(locationId: $locationId, start: $start, end: $end, includeDeleted: true, limit: $limit, offset: $offset) {
    id
    status
    deleted
    deletedBy { id name }
    deletionReason
    provider { id name }
    start
    duration
    type { name isBlockoff }
  }
}
"""


def fetch_all_appointments(token, location_id, start_iso, end_iso):
    # A single 60-day window at one location returned 2,412 raw appointments
    # in testing -- comfortably more than one page. Page with offset until a
    # page comes back short of PAGE_LIMIT, same pattern as every other sync
    # in this repo (fetchAllRows on the dashboard side, ENCOUNTERS_QUERY in
    # vetspire_clinical_sync.py).
    out = []
    offset = 0
    while True:
        result = gql(token, APPOINTMENTS_QUERY, {
            "locationId": location_id, "start": start_iso, "end": end_iso,
            "limit": PAGE_LIMIT, "offset": offset,
        })
        if "errors" in result:
            return out, result["errors"]
        page = (result.get("data") or {}).get("appointments") or []
        out.extend(page)
        if len(page) < PAGE_LIMIT:
            return out, None
        offset += PAGE_LIMIT


def _urlopen_with_retry(req, timeout):
    last_err = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.status
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last_err = e
        except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < RETRY_ATTEMPTS:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"    transient error ({last_err}) — retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            time.sleep(wait)
    raise last_err


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,
    })
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def supa_upsert(path, records, on_conflict):
    if not records:
        return []
    body = json.dumps(records).encode()
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/{path}?on_conflict={on_conflict}",
        data=body, method="POST",
        headers={
            "Content-Type":  "application/json",
            "apikey":        SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer":        "resolution=merge-duplicates,return=representation",
        },
    )
    try:
        body, _ = _urlopen_with_retry(req, timeout=20)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code} on {path}: {e.read().decode()[:300]}")
        return []


def date_chunks(start_str, end_str, chunk_days):
    d = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    while d <= end:
        chunk_end = min(d + timedelta(days=chunk_days - 1), end)
        yield d, chunk_end
        d = chunk_end + timedelta(days=1)


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip()
    token = token.removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    today = datetime.now(timezone.utc)
    totals = {"appointments": 0, "providers": 0, "cancelled_or_deleted": 0}

    for vetspire_loc_id, (loc_uuid, loc_name) in LOCATIONS.items():
        print(f"\n=== {loc_name} ({vetspire_loc_id}) ===")

        for chunk_start, chunk_end in date_chunks(SWEEP_FLOOR, today.strftime("%Y-%m-%d"), CHUNK_DAYS):
            start_iso = chunk_start.strftime("%Y-%m-%dT00:00:00Z")
            end_iso = (chunk_end + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
            appts, errors = fetch_all_appointments(token, vetspire_loc_id, start_iso, end_iso)
            if errors:
                print(f"  ERROR ({start_iso}..{end_iso}): {errors}")
                continue
            appts = [a for a in appts if not (a.get("type") or {}).get("isBlockoff")]
            if not appts:
                continue
            print(f"  {chunk_start.date()}..{chunk_end.date()}: {len(appts)} appointments (non-blockoff)")

            providers = {}
            for a in appts:
                for p in (a.get("provider"), a.get("deletedBy")):
                    if p and p.get("id"):
                        providers[p["id"]] = {"vetspire_provider_id": p["id"], "full_name": p.get("name"), "location_id": loc_uuid}
            provider_rows = supa_upsert("providers", list(providers.values()), "vetspire_provider_id")
            provider_uuid_by_vs = {r["vetspire_provider_id"]: r["id"] for r in provider_rows}
            totals["providers"] += len(provider_rows)

            event_rows = []
            for a in appts:
                provider_vs = (a.get("provider") or {}).get("id")
                deleted_by_vs = (a.get("deletedBy") or {}).get("id")
                status = a.get("status")
                deleted = bool(a.get("deleted"))
                if status in ("CANCELLED", "NOSHOW") or deleted:
                    totals["cancelled_or_deleted"] += 1
                event_rows.append({
                    "vetspire_appointment_id": a["id"],
                    "location_id": loc_uuid,
                    "provider_id": provider_uuid_by_vs.get(provider_vs),
                    "appointment_type": (a.get("type") or {}).get("name"),
                    "scheduled_start": a.get("start"),
                    "status": status,
                    "deleted": deleted,
                    "deleted_by_provider_id": provider_uuid_by_vs.get(deleted_by_vs),
                    "deletion_reason": a.get("deletionReason"),
                    "duration_minutes": a.get("duration"),
                })
            event_out = supa_upsert("appointment_events", event_rows, "vetspire_appointment_id")
            totals["appointments"] += len(event_out)

    print("\n=== Done ===")
    for k, v in totals.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
