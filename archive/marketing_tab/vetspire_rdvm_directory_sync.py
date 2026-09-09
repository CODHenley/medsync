#!/usr/bin/env python3
"""
vetspire_rdvm_directory_sync.py
Syncs a complete, standalone directory of every Vetspire Rdvm record (id,
name, address) into ScoutSync's rdvm_directory table -- independent of
any client/encounter/referral-relationship activity.

Why this exists: referral_relationships (synced by vetspire_clinical_sync.py)
only gets a row for an rDVM linked to a client with a RECENT encounter (that
script's rolling LOOKBACK_DAYS window, default 3 days). rdvm_revenue_daily
(synced by vetspire_financial_sync.py) covers a much wider window via
salesReport and is not tied to any specific client's encounter recency at
all -- so most rDVMs with real revenue attribution were never captured by
the encounter-triggered sync, and the Marketing tab's Revenue by Referring
Hospital section showed "rDVM <id>" instead of a real name for most rows,
with no postal code for the map either.

This is the fix: rdvms(limit, offset) is a complete, independent listing of
every Rdvm Vetspire has on file (confirmed live via
vetspire_rdvm_visit_mutation_probe.py -- standard limit/offset pagination,
~1,126 total records per rdvmsCount from vetspire_clinical_schema_probe.py),
with the same real address fields (addressLine1/city/state/postalCode)
already confirmed populated (20/20 sampled) when this Marketing tab was
first built. Syncing this directly means every rDVM has a name/address on
file regardless of whether any client referred by them has had a recent
encounter.

Usage:
  VETSPIRE_API_TOKEN="..." python3 vetspire_rdvm_directory_sync.py
"""
import json, time, urllib.request, urllib.error

VETSPIRE_URL = "https://api.vetspire.com/graphql"
SUPA_URL     = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

PAGE_SIZE = 200


def _urlopen_with_retry(req, timeout):
    """Same retry helper as vetspire_clinical_sync.py -- transient 5xx/network
    errors get retried with backoff, 4xx fails immediately."""
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
    body, _ = _urlopen_with_retry(req, timeout=20)
    return json.loads(body)


RDVMS_QUERY = """
query($limit: Int, $offset: Int) {
  rdvms(limit: $limit, offset: $offset) {
    id
    name
    isActive
    city
    state
    postalCode
  }
}
"""


def main():
    import os
    token = os.environ.get("VETSPIRE_API_TOKEN", "")
    if not token:
        print("ERROR: VETSPIRE_API_TOKEN not set")
        return

    print("=== Syncing full rDVM directory from Vetspire ===")
    offset = 0
    total_upserted = 0
    while True:
        result = gql(token, RDVMS_QUERY, {"limit": PAGE_SIZE, "offset": offset})
        if "errors" in result:
            print(f"  ERROR at offset {offset}: {result['errors']}")
            break
        rows = (result.get("data") or {}).get("rdvms") or []
        if not rows:
            break

        directory_rows = [{
            "vetspire_rdvm_id": r["id"],
            "name": r.get("name"),
            "is_active": r.get("isActive"),
            "city": r.get("city"),
            "state": r.get("state"),
            "postal_code": r.get("postalCode"),
        } for r in rows]

        out = supa_upsert("rdvm_directory", directory_rows, "vetspire_rdvm_id")
        print(f"  offset {offset}: fetched {len(rows)}, upserted {len(out)}")
        total_upserted += len(out)

        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"\n=== Done — {total_upserted} rdvm_directory rows upserted ===")


if __name__ == "__main__":
    main()
