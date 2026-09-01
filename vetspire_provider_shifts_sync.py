#!/usr/bin/env python3
"""
vetspire_provider_shifts_sync.py
Syncs Vetspire's provider shift schedules (Location.providerSchedules) into
ScoutSync's new provider_shifts table, and backfills locations.open_date
from Vetspire's own Location.openDate field.

Why this exists: the Days Closed & Financial Impact report needs to tell
"staff were scheduled but generated no revenue" apart from "actually
closed." Neither encounters nor billed revenue can make that distinction --
both only reflect patient-visit activity, not staff presence. Confirmed via
vetspire_scheduling_schema_probe.py / vetspire_location_root_query_probe.py
that Location.providerSchedules(startDate, endDate) returns one row per
provider per scheduled shift-day, independent of whether any encounter or
invoice happened that day -- exactly the staffing signal needed.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_provider_shifts_sync.py
"""
import json, os, urllib.request, urllib.error
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

# Floor for the historical sweep -- safely before any location's real
# openDate (Lincoln Park's, the oldest, is 2022-12-12 per Vetspire). A
# location simply returns no shifts before it existed, so a floor this
# early costs a few empty chunks, not incorrect data.
SWEEP_FLOOR = "2020-01-01"
CHUNK_DAYS = int(os.environ.get("CHUNK_DAYS", "120"))

LOCATION_QUERY = """
query($id: ID, $start: Date, $end: Date) {
  location(id: $id) {
    id
    openDate
    providerSchedules(startDate: $start, endDate: $end) {
      id
      start
      end
      providerId
      provider { id name }
    }
  }
}
"""


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
            import time; time.sleep(wait)
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
        yield d.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
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

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    totals = {"shifts": 0, "providers": 0, "locations_updated": 0}

    for vetspire_loc_id, (loc_uuid, loc_name) in LOCATIONS.items():
        print(f"\n=== {loc_name} ({vetspire_loc_id}) ===")
        open_date_captured = False

        for chunk_start, chunk_end in date_chunks(SWEEP_FLOOR, today, CHUNK_DAYS):
            result = gql(token, LOCATION_QUERY, {
                "id": vetspire_loc_id, "start": chunk_start, "end": chunk_end,
            })
            if "errors" in result:
                print(f"  ERROR ({chunk_start}..{chunk_end}): {result['errors']}")
                continue
            loc_data = (result.get("data") or {}).get("location") or {}

            if not open_date_captured and loc_data.get("openDate"):
                supa_upsert("locations", [{"id": loc_uuid, "open_date": loc_data["openDate"]}], "id")
                print(f"  open_date = {loc_data['openDate']}")
                open_date_captured = True
                totals["locations_updated"] += 1

            schedules = loc_data.get("providerSchedules") or []
            if not schedules:
                continue
            print(f"  {chunk_start}..{chunk_end}: {len(schedules)} shift-days")

            providers = {}
            for s in schedules:
                p = s.get("provider")
                if p and p.get("id"):
                    providers[p["id"]] = {"vetspire_provider_id": p["id"], "full_name": p.get("name"), "location_id": loc_uuid}
            provider_rows = supa_upsert("providers", list(providers.values()), "vetspire_provider_id")
            provider_uuid_by_vs = {r["vetspire_provider_id"]: r["id"] for r in provider_rows}
            totals["providers"] += len(provider_rows)

            shift_rows = []
            for s in schedules:
                pid = (s.get("provider") or {}).get("id")
                shift_rows.append({
                    "vetspire_shift_id": s["id"],
                    "location_id": loc_uuid,
                    "provider_id": provider_uuid_by_vs.get(pid),
                    "shift_start": s.get("start"),
                    "shift_end": s.get("end") or s.get("start"),
                })
            shift_out = supa_upsert("provider_shifts", shift_rows, "vetspire_shift_id")
            totals["shifts"] += len(shift_out)

    print("\n=== Done ===")
    for k, v in totals.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
