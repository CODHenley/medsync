#!/usr/bin/env python3
"""
vetspire_diagnosis_utilization_audit.py
By-provider fill-rate audit for Vetspire's structured diagnosis features
(Encounter.problems, Patient.patientDiagnoses) versus the free-text
appointment reason-for-visit (Appointment.reason) -- the two other candidate
"determined illness" signals in prior investigation.

Context: vetspire_clinical_schema_probe.py already established Problem and
PatientDiagnosis are effectively unused (0/300 encounters over 180 days,
0/20 patients sampled) while appointment.reason was populated on 233/300
(78%). This script exists to turn that spot-check into a real by-provider
breakdown over every provider at every location, so leadership has an actual
number per doctor rather than one practice-wide sample -- evidence for a
training/workflow push, not a code fix (there is nothing to sync until
providers start using the feature).

Report-only. No Supabase writes. Per this repo's convention, delete this
script in a follow-up commit once its results have been reported.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_diagnosis_utilization_audit.py --days 180
"""
import argparse, json, os, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

VETSPIRE_URL = "https://api.vetspire.com/graphql"

# vetspire_id -> location name -- same 4 locations as every other sync.
LOCATIONS = {
    "23083": "Lincoln Park",
    "27390": "Old Orchard",
    "24356": "West Loop",
    "28253": "Wheaton",
}

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

AUDIT_QUERY = """
query($locationId: ID, $updatedAtStart: NaiveDateTime, $updatedAtEnd: NaiveDateTime, $limit: Int, $offset: Int) {
  encounters(locationId: $locationId, updatedAtStart: $updatedAtStart, updatedAtEnd: $updatedAtEnd, limit: $limit, offset: $offset) {
    id
    provider { id name }
    appointment { reason }
    problems { id }
    patient { id patientDiagnoses { id } }
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
            print(f"    transient error ({last_err}) -- retrying in {wait}s (attempt {attempt}/{RETRY_ATTEMPTS})...")
            import time
            time.sleep(wait)
    raise last_err


def gql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(VETSPIRE_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": token,  # permanent API key -- no Bearer prefix
    })
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
        return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"  Vetspire HTTP {e.code}: {e.read().decode()[:300]}")
        return {"errors": [{"message": f"HTTP {e.code}"}]}


def load_token():
    token = os.environ.get("VETSPIRE_API_TOKEN", "").strip()
    if not token:
        token_file = os.path.expanduser("~/.vetspire_token")
        if os.path.exists(token_file):
            token = open(token_file).read().strip()
    return token.removeprefix("Bearer ").strip()


def pct(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=180, help="Trailing window in days")
    args = ap.parse_args()

    token = load_token()
    if not token:
        raise SystemExit("ERROR: VETSPIRE_API_TOKEN not set")

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%S")
    until = now.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"=== Diagnosis-feature utilization audit: trailing {args.days} days ({since} → {until}) ===\n")

    # provider_id -> {"name": ..., "location": ..., "encounters": 0, "reason": 0,
    #                 "problems": 0, "patient_ids_seen": set(), "patient_ids_with_dx": set()}
    by_provider = {}
    overall = {"encounters": 0, "reason": 0, "problems": 0}
    overall_patients_seen = set()
    overall_patients_with_dx = set()

    for vetspire_loc_id, loc_name in LOCATIONS.items():
        print(f"--- {loc_name} ---")
        offset = 0
        loc_encounters = 0
        while True:
            result = gql(token, AUDIT_QUERY, {
                "locationId": vetspire_loc_id,
                "updatedAtStart": since,
                "updatedAtEnd": until,
                "limit": 100,
                "offset": offset,
            })
            if "errors" in result:
                print(f"  ERROR: {result['errors']}")
                break
            rows = (result.get("data") or {}).get("encounters") or []
            if not rows:
                break

            for enc in rows:
                provider = enc.get("provider") or {}
                pid = provider.get("id")
                if not pid:
                    continue
                p = by_provider.setdefault(pid, {
                    "name": provider.get("name") or pid, "location": loc_name,
                    "encounters": 0, "reason": 0, "problems": 0,
                    "patient_ids_seen": set(), "patient_ids_with_dx": set(),
                })

                p["encounters"] += 1
                overall["encounters"] += 1
                loc_encounters += 1

                if (enc.get("appointment") or {}).get("reason"):
                    p["reason"] += 1
                    overall["reason"] += 1

                if enc.get("problems"):
                    p["problems"] += 1
                    overall["problems"] += 1

                patient = enc.get("patient") or {}
                pat_id = patient.get("id")
                if pat_id:
                    p["patient_ids_seen"].add(pat_id)
                    overall_patients_seen.add(pat_id)
                    if patient.get("patientDiagnoses"):
                        p["patient_ids_with_dx"].add(pat_id)
                        overall_patients_with_dx.add(pat_id)

            print(f"  fetched {len(rows)} encounters (offset {offset})")
            offset += 100

        print(f"  {loc_encounters} total encounters\n")

    print("=== By provider ===")
    header = f"{'Provider':<28} {'Location':<14} {'Encounters':>10} {'Reason %':>9} {'Problems %':>11} {'PatientDx %':>12}"
    print(header)
    print("-" * len(header))
    for pid, p in sorted(by_provider.items(), key=lambda kv: (kv[1]["location"], kv[1]["name"])):
        dx_pct = pct(len(p["patient_ids_with_dx"]), len(p["patient_ids_seen"]))
        print(f"{p['name']:<28} {p['location']:<14} {p['encounters']:>10} "
              f"{pct(p['reason'], p['encounters']):>9} {pct(p['problems'], p['encounters']):>11} {dx_pct:>12}")

    print("\n=== Overall ===")
    overall_dx_pct = pct(len(overall_patients_with_dx), len(overall_patients_seen))
    print(f"  {overall['encounters']} encounters across {len(by_provider)} providers, {len(LOCATIONS)} locations")
    print(f"  appointment.reason (free-text presenting complaint): {pct(overall['reason'], overall['encounters'])} filled")
    print(f"  problems (encounter-level problem list):             {pct(overall['problems'], overall['encounters'])} filled")
    print(f"  patientDiagnoses (chart-level diagnosis list):       {overall_dx_pct} filled ({len(overall_patients_seen)} distinct patients)")

    any_dx_usage = overall["problems"] > 0 or len(overall_patients_with_dx) > 0
    print(f"\n=== Conclusion: structured diagnosis features are "
          f"{'partially used -- see per-provider breakdown above' if any_dx_usage else 'completely unused across every provider and location'} ===")


if __name__ == "__main__":
    main()
