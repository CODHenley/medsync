#!/usr/bin/env python3
"""
vetspire_clinical_sync.py
Syncs Vetspire encounters (+ the patient/client/provider/referral data attached
to them) into ScoutSync's Clinical Operations tables — encounters, providers,
clients, patients, referral_relationships, records_release_log.

Field names and query arguments below are all confirmed via
vetspire_clinical_schema_probe.py against the production schema — see that
script's CI output for the source of truth, not inference.

Runs the same way as nightly_revenue_sync.py: pulls a trailing window
(today + a lookback buffer) so every run is self-healing regardless of
whether the previous run succeeded, and upserts on each table's
vetspire_*_id unique key so re-runs are idempotent.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_clinical_sync.py
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# vetspire_id -> (Supabase locations.id, name) — same 4 locations as every other sync.
LOCATIONS = {
    "23083": ("11111111-0000-0000-0000-000000000001", "Lincoln Park"),
    "27390": ("11111111-0000-0000-0000-000000000002", "Old Orchard"),
    "24356": ("11111111-0000-0000-0000-000000000003", "West Loop"),
    "28253": ("11111111-0000-0000-0000-000000000004", "Wheaton"),
}

LOOKBACK_DAYS = 3  # overlap window so a missed run gets caught by the next one

ENCOUNTERS_QUERY = """
query($locationId: ID, $updatedAtStart: NaiveDateTime, $updatedAtEnd: NaiveDateTime, $limit: Int, $offset: Int) {
  encounters(locationId: $locationId, updatedAtStart: $updatedAtStart, updatedAtEnd: $updatedAtEnd, limit: $limit, offset: $offset) {
    id
    start
    signedDatetime
    visitType
    provider { id name }
    patient {
      id
      species
      client {
        id
        givenName
        familyName
        insertedAt
        customReferralSource
        clientReferralSource { name }
        clientRdvms {
          id
          insertedAt
          rdvm {
            id
            name
            documents { id name insertedAt }
          }
        }
      }
    }
    appointment {
      id
      checkedInAt
      startedAt
      completedAt
    }
  }
}
"""


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type":  "application/json",
        "Authorization": token,  # permanent API key — no Bearer prefix
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
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
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Supabase error {e.code} on {path}: {e.read().decode()[:300]}")
        return []


def main():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip()
    token = token.removeprefix("Bearer ").strip()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    # Vetspire's GraphQL API is Absinthe/Elixir-based (confirmed by its Phoenix-token
    # auth and Elixir-style field names elsewhere) — its NaiveDateTime scalar expects
    # a naive ISO string with no timezone offset, unlike Python's aware .isoformat().
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    until = now.strftime("%Y-%m-%dT%H:%M:%S")

    totals = {"encounters": 0, "clients": 0, "patients": 0, "providers": 0,
              "referral_relationships": 0, "records_release_log": 0}

    for vetspire_loc_id, (loc_uuid, loc_name) in LOCATIONS.items():
        print(f"\n=== {loc_name} ({vetspire_loc_id}) ===")
        offset = 0
        while True:
            result = gql(token, ENCOUNTERS_QUERY, {
                "locationId": vetspire_loc_id,
                "updatedAtStart": since,
                "updatedAtEnd": until,
                "limit": 100,
                "offset": offset,
            })
            if "errors" in result:
                print(f"  ERROR: {result['errors']}")
                break
            rows = result.get("data", {}).get("encounters") or []
            if not rows:
                break
            print(f"  fetched {len(rows)} encounters (offset {offset})")

            providers, clients, patients = {}, {}, {}
            referral_rows, release_rows, encounter_rows = [], [], []

            for enc in rows:
                provider = enc.get("provider")
                patient = enc.get("patient") or {}
                client = patient.get("client") or {}
                appt = enc.get("appointment") or {}

                if provider and provider.get("id"):
                    providers[provider["id"]] = {
                        "vetspire_provider_id": provider["id"],
                        "full_name": provider.get("name"),
                        "location_id": loc_uuid,
                    }

                if client.get("id"):
                    clients[client["id"]] = {
                        "vetspire_client_id": client["id"],
                        "location_id": loc_uuid,
                    }
                    for cr in (client.get("clientRdvms") or []):
                        rdvm = cr.get("rdvm") or {}
                        if not rdvm.get("id"):
                            continue
                        referral_rows.append({
                            "vetspire_referral_id": cr["id"],
                            "vetspire_client_id": client["id"],  # resolved to client_id below
                            "referral_name": rdvm.get("name"),
                            "referral_type": "other",  # needs manual classification — see below
                            "listed_at": cr.get("insertedAt"),
                        })
                        for doc in (rdvm.get("documents") or []):
                            release_rows.append({
                                "vetspire_release_id": doc["id"],
                                "vetspire_client_id": client["id"],
                                "vetspire_referral_id": cr["id"],
                                "released_at": doc.get("insertedAt"),
                                "method": "vetspire_document",
                            })

                if patient.get("id"):
                    patients[patient["id"]] = {
                        "vetspire_patient_id": patient["id"],
                        "vetspire_client_id": client.get("id"),  # resolved to client_id below
                        "species": patient.get("species"),
                    }

                encounter_rows.append({
                    "vetspire_encounter_id": enc["id"],
                    "location_id": loc_uuid,
                    "vetspire_client_id": client.get("id"),
                    "vetspire_patient_id": patient.get("id"),
                    "vetspire_provider_id": (provider or {}).get("id"),
                    "visit_type": enc.get("visitType"),
                    "checked_in_at": appt.get("checkedInAt"),
                    "started_at": enc.get("start") or appt.get("startedAt"),
                    "completed_at": appt.get("completedAt") or enc.get("signedDatetime"),
                })

            # ── Upsert dimension tables first, capture their real Supabase uuids ──
            provider_rows = supa_upsert("providers", list(providers.values()), "vetspire_provider_id")
            provider_uuid_by_vs = {r["vetspire_provider_id"]: r["id"] for r in provider_rows}

            client_rows = supa_upsert("clients", list(clients.values()), "vetspire_client_id")
            client_uuid_by_vs = {r["vetspire_client_id"]: r["id"] for r in client_rows}

            for p in patients.values():
                p["client_id"] = client_uuid_by_vs.get(p.pop("vetspire_client_id"))
            patient_rows = supa_upsert("patients", list(patients.values()), "vetspire_patient_id")
            patient_uuid_by_vs = {r["vetspire_patient_id"]: r["id"] for r in patient_rows}

            for r in referral_rows:
                r["client_id"] = client_uuid_by_vs.get(r.pop("vetspire_client_id"))
            referral_out = supa_upsert("referral_relationships", referral_rows, "vetspire_referral_id")
            referral_uuid_by_vs = {r["vetspire_referral_id"]: r["id"] for r in referral_out}

            for r in release_rows:
                r["client_id"] = client_uuid_by_vs.get(r.pop("vetspire_client_id"))
                r["referral_relationship_id"] = referral_uuid_by_vs.get(r.pop("vetspire_referral_id"))
            release_out = supa_upsert("records_release_log", release_rows, "vetspire_release_id")

            # ── Now the encounters themselves, with resolved FKs ──
            for e in encounter_rows:
                e["provider_id"] = provider_uuid_by_vs.get(e.pop("vetspire_provider_id"))
                e["client_id"] = client_uuid_by_vs.get(e.pop("vetspire_client_id"))
                e["patient_id"] = patient_uuid_by_vs.get(e.pop("vetspire_patient_id"))
            encounter_out = supa_upsert("encounters", encounter_rows, "vetspire_encounter_id")

            totals["providers"] += len(provider_rows)
            totals["clients"] += len(client_rows)
            totals["patients"] += len(patient_rows)
            totals["referral_relationships"] += len(referral_out)
            totals["records_release_log"] += len(release_out)
            totals["encounters"] += len(encounter_out)

            if len(rows) < 100:
                break
            offset += 100

    print("\n=== Done ===")
    for k, v in totals.items():
        print(f"  {k}: {v}")
    print(
        "\nNOTE: every referral_relationships row lands with referral_type='other' — "
        "distinguishing a true rDVM from a competitor urgent care/ER needs a one-time "
        "human classification pass (e.g. via Rdvm.tags in Vetspire), not something "
        "this sync can infer on its own."
    )


if __name__ == "__main__":
    main()
