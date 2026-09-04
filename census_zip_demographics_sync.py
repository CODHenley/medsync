#!/usr/bin/env python3
"""
census_zip_demographics_sync.py
Pulls U.S. Census ACS 5-year estimates (median household income, population,
median age, average household size) for every real client ZIP code ScoutSync
has ever seen a case from (v_case_geo.postal_code -- actual service-area
ZIPs, not a hardcoded map-plotting list), and upserts them into
zip_demographics.

Feeds the de novo location-ramp-up projection: a new location's service-area
profile (weighted average of these figures across its own client ZIP mix)
gets compared against mature locations' profiles, so the projection is
benchmarked against demographically/economically similar locations, not a
flat average of all of them.

No API key required for this volume (Census allows a modest number of
unauthenticated requests/day; this project's real ZIP count is nowhere near
that ceiling) -- set CENSUS_API_KEY to raise the ceiling if that ever
changes.

Usage:
  python3 census_zip_demographics_sync.py
  ACS_VINTAGE_YEAR=2022 python3 census_zip_demographics_sync.py
"""
import json, os, re, time, urllib.parse, urllib.request, urllib.error

SUPA_URL = "https://aemkdummdrmxtwrkggjw.supabase.co"
SUPA_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s"

# ACS 5-year estimates -- released annually, roughly a year behind. Bump this
# once a newer vintage is confirmed published; the variable codes themselves
# are stable across vintages.
ACS_VINTAGE_YEAR = os.environ.get("ACS_VINTAGE_YEAR", "2022")
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()

ACS_VARS = {
    "B19013_001E": "median_household_income",
    "B01003_001E": "population",
    "B01002_001E": "median_age",
    "B25010_001E": "avg_household_size",
}

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


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
            time.sleep(wait)
    raise last_err


def supa_get_all(path, params, page_size=1000):
    out = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPA_URL}/rest/v1/{path}?{params}&limit={page_size}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"},
        )
        body, _ = _urlopen_with_retry(req, timeout=30)
        page = json.loads(body)
        out.extend(page)
        if len(page) < page_size:
            return out
        offset += page_size


def supa_upsert(records):
    if not records:
        return 201
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/zip_demographics?on_conflict=zip_code",
        data=json.dumps(records).encode(),
        headers={
            "Content-Type": "application/json",
            "apikey": SUPA_KEY,
            "Authorization": f"Bearer {SUPA_KEY}",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    req.get_method = lambda: "POST"
    body, status = _urlopen_with_retry(req, timeout=30)
    return status


def fetch_acs_batch(zip_codes):
    """One Census API call per batch of ZCTAs (comma-separated `for` clause
    -- far cheaper than one request per ZIP, and well under any URL-length
    limit for the batch sizes used here)."""
    get_vars = ",".join(ACS_VARS.keys())
    zctas = ",".join(zip_codes)
    query = {
        "get": get_vars,
        "for": f"zip code tabulation area:{zctas}",
    }
    if CENSUS_API_KEY:
        query["key"] = CENSUS_API_KEY
    url = f"https://api.census.gov/data/{ACS_VINTAGE_YEAR}/acs/acs5?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url)
    try:
        body, _ = _urlopen_with_retry(req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"  Census API error {e.code} for batch of {len(zip_codes)}: {e.read().decode()[:300]}")
        return []
    try:
        rows = json.loads(body)
    except json.JSONDecodeError:
        # The Census API sometimes answers a malformed query with a 200 and
        # a non-JSON (often empty or HTML) body instead of a real error
        # status -- skip this one batch rather than crashing the whole sync.
        print(f"  Census API returned non-JSON for batch of {len(zip_codes)}: {body[:300]!r}")
        return []
    header, data_rows = rows[0], rows[1:]
    col_idx = {name: i for i, name in enumerate(header)}
    zcta_idx = col_idx["zip code tabulation area"]
    results = []
    for row in data_rows:
        rec = {"zip_code": row[zcta_idx], "acs_vintage": ACS_VINTAGE_YEAR}
        for var_code, field_name in ACS_VARS.items():
            raw = row[col_idx[var_code]]
            try:
                val = float(raw)
                # Census uses large negative sentinel codes (e.g. -666666666)
                # for "not available/not computed" -- never store those as a
                # real figure.
                rec[field_name] = val if val >= 0 else None
            except (TypeError, ValueError):
                rec[field_name] = None
        results.append(rec)
    return results


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def main():
    print(f"=== Census ZIP demographics sync (ACS {ACS_VINTAGE_YEAR} 5-year) ===\n")

    geo_rows = supa_get_all("v_case_geo", "select=postal_code")
    raw_zips = sorted({(r.get("postal_code") or "").strip() for r in geo_rows if r.get("postal_code")})
    print(f"{len(raw_zips)} distinct real client postal_code values found in v_case_geo")

    # Client postal_code is free-typed in Vetspire -- ZIP+4 ("60614-1234"),
    # stray whitespace, or non-US codes have shown up before. The Census
    # ZCTA `for` clause is a single comma-separated string; one malformed
    # entry can make the ENTIRE batch it's in come back non-JSON instead of
    # a clean per-item error, so filter to plain 5-digit ZIPs up front
    # rather than discovering that one bad value at request time.
    zip_codes = sorted({z[:5] for z in raw_zips if re.fullmatch(r"\d{5}(-\d{4})?", z)})
    dropped = len(raw_zips) - len(zip_codes)
    if dropped:
        not_5digit = [z for z in raw_zips if not re.fullmatch(r"\d{5}(-\d{4})?", z)][:10]
        print(f"  {dropped} value(s) weren't a plain 5-digit (or ZIP+4) US ZIP, skipped: {not_5digit}")
    print(f"{len(zip_codes)} valid 5-digit ZIPs to look up\n")

    if not zip_codes:
        print("No valid ZIP codes to look up -- nothing to do.")
        return

    all_records = []
    errors = 0
    # Batches of 40 ZCTAs per call -- comfortably under any practical URL
    # length limit while keeping the total call count small.
    batches = list(chunks(zip_codes, 40))
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)} ({len(batch)} ZIPs)...", end=" ")
        records = fetch_acs_batch(batch)
        if not records:
            errors += 1
            print("no data returned")
            continue
        all_records.extend(records)
        print(f"got {len(records)}")

    found_zips = {r["zip_code"] for r in all_records}
    missing = sorted(set(zip_codes) - found_zips)
    if missing:
        print(f"\n{len(missing)} ZIP(s) had no ACS match (invalid ZCTA, or too new/small to be tabulated): {missing[:20]}{' ...' if len(missing) > 20 else ''}")

    upserted = 0
    for batch in chunks(all_records, 500):
        status = supa_upsert(batch)
        if str(status).startswith("2"):
            upserted += len(batch)
        else:
            print(f"  Supabase upsert failed for a batch of {len(batch)}: HTTP {status}")
            errors += 1

    print(f"\n=== Done: {upserted} ZIP demographic profiles upserted, {errors} error(s) ===")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
