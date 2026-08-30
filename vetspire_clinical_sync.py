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
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2  # 2s, 4s between attempts


def _urlopen_with_retry(req, timeout):
    """Retries transient failures (5xx, connection resets, timeouts) with backoff.
    4xx errors are raised immediately -- retrying a bad request won't help.
    Without this, a single Supabase HTTP 500 or a dropped TLS connection killed
    the whole run outright instead of costing a few seconds."""
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

# referral_type classification: Vetspire's rdvmsCount showed 1,126 total rDVM
# records with zero tags applied — tagging all of them by hand isn't practical.
# Instead this defaults every relationship to 'rdvm_primary_care' (a Vetspire
# "Rdvm" record is, by definition, a referring vet) and only overrides to a
# competitor classification when the rDVM carries one of these two exact tag
# names — so Megan only has to tag the specific competitor urgent cares/ERs
# she already knows about in Vetspire, not the full list.
COMPETITOR_TAG_TO_REFERRAL_TYPE = {
    "competitor - urgent care": "competitor_urgent_care",
    "competitor - er": "competitor_er",
}


def classify_referral_type(rdvm_tags):
    for t in (rdvm_tags or []):
        mapped = COMPETITOR_TAG_TO_REFERRAL_TYPE.get((t.get("name") or "").strip().lower())
        if mapped:
            return mapped
    return "rdvm_primary_care"


# "Visits / Provider" should only count visits where an exam was actually
# performed — per Megan, any invoice line item with "Exam" in its name (this
# excludes med refills, drop-offs, and other non-exam services). Vetspire's
# Encounter.visitType turned out to be unpopulated in production (confirmed
# via vetspire_clinical_schema_probe.py — every sampled encounter had
# visitType=null), so the invoice line items are the only real signal here.
def had_exam(encounter_products):
    return any("exam" in (p.get("name") or "").lower() for p in (encounter_products or []))


def to_date(dt_str):
    return (dt_str or "")[:10] or None


# Client.addresses is confirmed sparse (2/20 sampled clients had any address
# on file) and a client can have more than one -- prefer the one flagged
# isPrimary, else just take the first, and only keep it if it actually has a
# postal_code (some records return address rows with every field blank).
def pick_address(addresses):
    addresses = [a for a in (addresses or []) if a.get("postalCode")]
    if not addresses:
        return None
    for a in addresses:
        if a.get("isPrimary"):
            return a
    return addresses[0]


# vetspire_id -> (Supabase locations.id, name) — same 4 locations as every other sync.
LOCATIONS = {
    "23083": ("11111111-0000-0000-0000-000000000001", "Lincoln Park"),
    "27390": ("11111111-0000-0000-0000-000000000002", "Old Orchard"),
    "24356": ("11111111-0000-0000-0000-000000000003", "West Loop"),
    "28253": ("11111111-0000-0000-0000-000000000004", "Wheaton"),
}

LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "3"))
# Default 3 = overlap window so a missed scheduled run gets caught by the next
# one. Override via the LOOKBACK_DAYS env var (or the workflow_dispatch input)
# for a one-time historical backfill — this sync has only ever run with the
# default 3-day window since it went live, so encounters (and everything
# built on it, like v_clinical_kpis_daily) has real data for only the last
# few days; anything wider (e.g. a 30-day chart) is mostly zeros before a
# backfill closes the gap. Filters on updatedAt, not the visit date itself,
# but for already-closed/signed encounters the two are normally close
# together, so widening this window does capture real historical visits —
# same mechanism the routine 4-hour sync already relies on.

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
            tags { name }
            documents { id name insertedAt }
          }
        }
        addresses { id city state postalCode isPrimary }
      }
    }
    appointment {
      id
      checkedInAt
      startedAt
      completedAt
      reason
    }
    encounterProducts { name }
    diagnostics { id name providerId }
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
              "referral_relationships": 0, "records_release_log": 0,
              "encounter_diagnostics": 0}

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
            referrals, releases, diagnostics = {}, {}, {}
            encounter_rows = []

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
                    addr = pick_address(client.get("addresses"))
                    clients[client["id"]] = {
                        "vetspire_client_id": client["id"],
                        "location_id": loc_uuid,
                        "city": (addr or {}).get("city"),
                        "state": (addr or {}).get("state"),
                        "postal_code": (addr or {}).get("postalCode"),
                    }
                    for cr in (client.get("clientRdvms") or []):
                        rdvm = cr.get("rdvm") or {}
                        if not rdvm.get("id"):
                            continue
                        # Keyed by vetspire id (not appended to a list) — the same
                        # ClientRdvm/document reappears once per encounter for that
                        # client, and Postgres's ON CONFLICT DO UPDATE errors out if
                        # a single upsert call contains the same conflict key twice.
                        referrals[cr["id"]] = {
                            "vetspire_referral_id": cr["id"],
                            "vetspire_client_id": client["id"],  # resolved to client_id below
                            "referral_name": rdvm.get("name"),
                            "referral_type": classify_referral_type(rdvm.get("tags")),
                            "listed_at": cr.get("insertedAt"),
                        }
                        for doc in (rdvm.get("documents") or []):
                            releases[doc["id"]] = {
                                "vetspire_release_id": doc["id"],
                                "vetspire_client_id": client["id"],
                                "vetspire_referral_id": cr["id"],
                                "released_at": doc.get("insertedAt"),
                                "method": "vetspire_document",
                            }

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
                    "had_exam": had_exam(enc.get("encounterProducts")),
                    "chief_complaint": appt.get("reason"),
                })

                # Diagnostics = tests/procedures ordered this encounter (Vetspire's
                # Diagnostic type — not a clinical diagnosis/condition, confirmed via
                # the schema probe). Keyed by vetspire id, same dedup reasoning as
                # referrals/releases above. encounter_id/provider_id resolved below
                # once encounter_uuid_by_vs exists.
                for diag in (enc.get("diagnostics") or []):
                    if not diag.get("id"):
                        continue
                    diagnostics[diag["id"]] = {
                        "vetspire_diagnostic_id": diag["id"],
                        "vetspire_encounter_id": enc["id"],
                        "location_id": loc_uuid,
                        "vetspire_provider_id": diag.get("providerId"),
                        "name": diag.get("name"),
                        "service_date": to_date(enc.get("start") or appt.get("startedAt")),
                    }

            # ── Upsert dimension tables first, capture their real Supabase uuids ──
            provider_rows = supa_upsert("providers", list(providers.values()), "vetspire_provider_id")
            provider_uuid_by_vs = {r["vetspire_provider_id"]: r["id"] for r in provider_rows}

            client_rows = supa_upsert("clients", list(clients.values()), "vetspire_client_id")
            client_uuid_by_vs = {r["vetspire_client_id"]: r["id"] for r in client_rows}

            for p in patients.values():
                p["client_id"] = client_uuid_by_vs.get(p.pop("vetspire_client_id"))
            patient_rows = supa_upsert("patients", list(patients.values()), "vetspire_patient_id")
            patient_uuid_by_vs = {r["vetspire_patient_id"]: r["id"] for r in patient_rows}

            for r in referrals.values():
                r["client_id"] = client_uuid_by_vs.get(r.pop("vetspire_client_id"))
            referral_out = supa_upsert("referral_relationships", list(referrals.values()), "vetspire_referral_id")
            referral_uuid_by_vs = {r["vetspire_referral_id"]: r["id"] for r in referral_out}

            for r in releases.values():
                r["client_id"] = client_uuid_by_vs.get(r.pop("vetspire_client_id"))
                r["referral_relationship_id"] = referral_uuid_by_vs.get(r.pop("vetspire_referral_id"))
            release_out = supa_upsert("records_release_log", list(releases.values()), "vetspire_release_id")

            # ── Now the encounters themselves, with resolved FKs ──
            for e in encounter_rows:
                e["provider_id"] = provider_uuid_by_vs.get(e.pop("vetspire_provider_id"))
                e["client_id"] = client_uuid_by_vs.get(e.pop("vetspire_client_id"))
                e["patient_id"] = patient_uuid_by_vs.get(e.pop("vetspire_patient_id"))
            encounter_out = supa_upsert("encounters", encounter_rows, "vetspire_encounter_id")
            encounter_uuid_by_vs = {r["vetspire_encounter_id"]: r["id"] for r in encounter_out}

            for d in diagnostics.values():
                vs_provider_id = d.pop("vetspire_provider_id")
                d["provider_id"] = provider_uuid_by_vs.get(str(vs_provider_id)) if vs_provider_id else None
                d["encounter_id"] = encounter_uuid_by_vs.get(d.pop("vetspire_encounter_id"))
            diagnostic_out = supa_upsert("encounter_diagnostics", list(diagnostics.values()), "vetspire_diagnostic_id")

            totals["providers"] += len(provider_rows)
            totals["clients"] += len(client_rows)
            totals["patients"] += len(patient_rows)
            totals["referral_relationships"] += len(referral_out)
            totals["records_release_log"] += len(release_out)
            totals["encounters"] += len(encounter_out)
            totals["encounter_diagnostics"] += len(diagnostic_out)

            if len(rows) < 100:
                break
            offset += 100

    print("\n=== Done ===")
    for k, v in totals.items():
        print(f"  {k}: {v}")
    print(
        "\nNOTE: referral_type defaults to 'rdvm_primary_care' unless the rDVM in "
        "Vetspire carries the tag 'Competitor - Urgent Care' or 'Competitor - ER' "
        "(exact names, case-insensitive) — tag the specific competitor practices "
        "you know about in Vetspire; everything else is assumed to be a real "
        "referring vet, since tagging all 1,126 rDVM records by hand isn't practical."
    )


if __name__ == "__main__":
    main()
