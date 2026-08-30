#!/usr/bin/env python3
"""
vetspire_clinical_schema_probe.py
Discovers the real Vetspire GraphQL field/type names needed for ScoutSync's
Clinical Operations and Financial sections — encounter-start ("arrived") events,
referral/rDVM relationships, records-release logging, provider/staff roster,
and invoice line-item detail.

This only runs where the environment has network access to api.vetspire.com
(it is blocked by policy in this Claude Code Remote session — run it locally
or wire it into a GitHub Actions step, same as wheaton_lot_sync.py).

Usage:
  python3 vetspire_clinical_schema_probe.py --token-file ~/.vetspire_token
  python3 vetspire_clinical_schema_probe.py --token "Bearer eyJ..."
"""
import sys, json, argparse, urllib.request, urllib.error

VETSPIRE_URL = 'https://api.vetspire.com/graphql'

KEYWORDS = [
    'encounter', 'appointment', 'arrive', 'checkin', 'check_in',
    'referral', 'rdvm', 'referring',
    'record', 'release', 'transfer', 'communication', 'letter',
    'client', 'patient', 'provider', 'staff', 'employee',
    'invoice', 'sale', 'transaction', 'charge', 'payment',
]


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    # The permanent API key (VETSPIRE_API_TOKEN) goes in raw, no "Bearer " prefix —
    # same auth pattern as wheaton_lot_sync.py / nightly_revenue_sync.py.
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def type_name(t):
    return t.get('name') or (t.get('ofType') or {}).get('name') or t.get('kind')


def dump_type_fields(token, type_name_str):
    r = gql(token, f'{{ __type(name: "{type_name_str}") {{ name fields {{ name type {{ name kind ofType {{ name kind ofType {{ name }} }} }} }} }} }}')
    data = (r.get('data') or {}).get('__type')
    if not data:
        print(f'  (type "{type_name_str}" not found — errors: {r.get("errors")})')
        return
    print(f'=== {type_name_str} fields ===')
    for f in sorted(data['fields'], key=lambda x: x['name']):
        tname = type_name(f['type'])
        flag = ' ***' if any(k in f['name'].lower() for k in KEYWORDS) else ''
        print(f'  {f["name"]}: {tname}{flag}')
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--token-file')
    args = parser.parse_args()

    if args.token_file:
        import os
        with open(os.path.expanduser(args.token_file)) as f:
            args.token = f.read().strip()
    if not args.token:
        print('ERROR: provide --token or --token-file')
        raise SystemExit(1)
    args.token = args.token.strip().removeprefix('Bearer ').strip()

    print('=== Connection test ===')
    try:
        r = gql(args.token, '{ __typename }')
        print(f'OK: {r}\n')
    except urllib.error.HTTPError as e:
        print(f'FAILED: HTTP {e.code} — {e.read()[:300]}')
        raise SystemExit(1)

    # 1. All root Query fields matching our keywords — tells us what's queryable at all
    print('=== Query root fields matching keywords ===')
    r = gql(args.token, '{ __schema { queryType { fields { name description } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    for f in fields:
        name = f.get('name', '')
        if any(k in name.lower() for k in KEYWORDS):
            print(f'  ★ {name}: {f.get("description", "")}')
    print(f'  (Total query fields: {len(fields)})\n')

    # 2. All schema type names matching our keywords — tells us the real object type names
    #    (e.g. it might be "Appointment" not "Encounter", "ReferralSource" not "Referral")
    print('=== Schema type names matching keywords ===')
    r = gql(args.token, '{ __schema { types { name kind } } }')
    types = (r.get('data') or {}).get('__schema', {}).get('types', [])
    candidates = sorted(
        t['name'] for t in types
        if t['kind'] == 'OBJECT' and any(k in t['name'].lower() for k in KEYWORDS)
    )
    for name in candidates:
        print(f'  ★ {name}')
    print()

    # 3. Dump fields for the most likely candidates outright (safe no-ops if they don't exist)
    likely_types = [
        'Patient', 'Client', 'Encounter', 'Appointment', 'Visit',
        'Referral', 'ReferralSource', 'Provider', 'Staff', 'Employee',
        'Invoice', 'InvoiceLineItem', 'Transaction',
    ]
    # Merge in whatever the keyword scan actually found, de-duped, so we don't miss
    # a type named something we didn't guess (e.g. "ClientReferral").
    all_targets = sorted(set(likely_types) | set(candidates))
    for t in all_targets:
        dump_type_fields(args.token, t)

    # 4. Argument signatures for the specific root query fields the actual clinical sync
    # will call — field names alone aren't enough to write working queries, and guessing
    # args wrong here means a wasted CI run same as the earlier auth-header mistake.
    sync_targets = [
        'encountersUpdatedSince', 'encounters', 'listEncounters',
        'patients', 'patient', 'clients', 'client',
        'providers', 'provider', 'appointments', 'countNewClients',
        'clientReferralSources',
    ]
    print('=== Args for the query fields the clinical sync will call ===')
    r = gql(args.token, '{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    by_name = {f['name']: f for f in fields}
    for name in sync_targets:
        f = by_name.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        arg_strs = []
        for a in f.get('args', []):
            arg_strs.append(f"{a['name']}: {type_name(a['type'])}")
        print(f"  {name}({', '.join(arg_strs) if arg_strs else '(no args)'})")
    print()

    # 5. salesReport/salesTypedReport args + their breakdown enum's real values, then a
    # live test call built ONLY from what was just introspected (no hardcoded enum
    # value guesses) — today's revenue sync calls salesReport with no breakdown arg at
    # all and gets one row per location/date (just `total`); Financial KPIs (ATC,
    # Revenue by Source, Revenue per Vet) need the row-level detail breakdown unlocks.
    print('=== salesReport / salesTypedReport args ===')
    sales_arg_types = {}  # field_name -> {arg_name: type_name}
    for name in ['salesReport', 'salesTypedReport']:
        f = by_name.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        sales_arg_types[name] = {}
        for a in f.get('args', []):
            tname = type_name(a['type'])
            sales_arg_types[name][a['name']] = tname
            print(f"  {name}.{a['name']}: {tname}")
    print()

    print('=== Breakdown enum values ===')
    breakdown_enum_values = {}  # arg_type_name -> [values]
    for field_name, arg_types in sales_arg_types.items():
        for arg_name, tname in arg_types.items():
            if 'breakdown' not in arg_name.lower() or tname in breakdown_enum_values:
                continue
            r = gql(args.token, f'{{ __type(name: "{tname}") {{ name enumValues {{ name }} }} }}')
            data = (r.get('data') or {}).get('__type')
            if not data:
                print(f'  (type "{tname}" not found)')
                continue
            values = [v['name'] for v in (data.get('enumValues') or [])]
            breakdown_enum_values[tname] = values
            print(f"  {tname}: {values}")
    print()

    print('=== Live salesReport test w/ breakdown (built from the above, not guessed) ===')
    sr_args = sales_arg_types.get('salesReport', {})
    breakdown_arg_name = next((a for a in sr_args if 'breakdown' in a.lower()), None)
    if breakdown_arg_name and breakdown_enum_values:
        enum_type = sr_args[breakdown_arg_name]
        values = breakdown_enum_values.get(enum_type, [])
        provider_val = next((v for v in values if 'PROVIDER' in v), None)
        category_val = next((v for v in values if 'CATEGORY' in v), None)
        test_breakdown = [v for v in (provider_val, category_val) if v] or values[:2]
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        test_query = f'''
        query($lids:[ID!], $s:Date, $e:Date, $bd:[{enum_type}!]){{
            salesReport(locationIds:$lids, startDate:$s, endDate:$e, {breakdown_arg_name}:$bd)
        }}
        '''
        r = gql(args.token, test_query, {
            'lids': ['28253'], 's': yesterday, 'e': yesterday, 'bd': test_breakdown,
        })
        print(f'  breakdown used: {test_breakdown}')
        print(f'  result: {json.dumps(r)[:3000]}')
    else:
        print('  (no breakdown arg found on salesReport — skipping live test)')
    print()

    # 6. The prior live test returned "date":"2026-08" (month-level) for a single-day
    # query — checking the `segment` arg's real enum values before assuming daily
    # financial granularity is even possible, rather than guessing DAY/DAILY as a string.
    print('=== ReportSegment enum values + live test with segment set ===')
    segment_arg_name = next((a for a in sr_args if 'segment' in a.lower()), None)
    if segment_arg_name:
        seg_type = sr_args[segment_arg_name]
        r = gql(args.token, f'{{ __type(name: "{seg_type}") {{ name enumValues {{ name }} }} }}')
        data = (r.get('data') or {}).get('__type')
        seg_values = [v['name'] for v in (data or {}).get('enumValues', [])] if data else []
        print(f"  {seg_type}: {seg_values}")
        day_val = next((v for v in seg_values if 'DAY' in v), None)
        if day_val and breakdown_arg_name and breakdown_enum_values:
            enum_type = sr_args[breakdown_arg_name]
            values = breakdown_enum_values.get(enum_type, [])
            provider_val = next((v for v in values if 'PROVIDER' in v), None)
            test_breakdown = [v for v in (provider_val,) if v] or values[:1]
            test_query = f'''
            query($lids:[ID!], $s:Date, $e:Date, $bd:[{enum_type}!], $seg:{seg_type}){{
                salesReport(locationIds:$lids, startDate:$s, endDate:$e, {breakdown_arg_name}:$bd, {segment_arg_name}:$seg)
            }}
            '''
            r2 = gql(args.token, test_query, {
                'lids': ['28253'], 's': yesterday, 'e': yesterday,
                'bd': test_breakdown, 'seg': day_val,
            })
            print(f'  segment used: {day_val}, breakdown used: {test_breakdown}')
            print(f'  result: {json.dumps(r2)[:2000]}')
        else:
            print('  (no DAY-like segment value found, or no breakdown to pair it with)')
    else:
        print('  (no segment arg found on salesReport)')
    print()

    # 7. referral_type classification (true rDVM vs. competitor urgent care/ER):
    # Rdvm.tags: EntityTag was confirmed in a prior run, but EntityTag itself was
    # never dumped (it doesn't match any KEYWORDS substring), and neither did the
    # root `rdvms` query field's args. Both needed before designing a classification
    # sync — plus a live sample of what's actually tagged today, so we design against
    # real data instead of assuming Megan has (or hasn't) already tagged anything.
    print('=== EntityTag fields ===')
    dump_type_fields(args.token, 'EntityTag')

    print('=== rdvms / rdvmsCount / searchRdvms args ===')
    r = gql(args.token, '{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    by_name2 = {f['name']: f for f in fields}
    for name in ['rdvms', 'rdvmsCount', 'searchRdvms']:
        f = by_name2.get(name)
        if not f:
            print(f'  (query field "{name}" not found)')
            continue
        arg_strs = [f"{a['name']}: {type_name(a['type'])}" for a in f.get('args', [])]
        print(f"  {name}({', '.join(arg_strs) if arg_strs else '(no args)'})")
    print()

    print('=== Live sample: first 50 rdvms with their tags ===')
    r = gql(args.token, '{ rdvms(limit: 50) { id name isActive tags { id name } } }')
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rdvms = (r.get('data') or {}).get('rdvms') or []
        print(f'  fetched {len(rdvms)} rdvms')
        tag_names = set()
        for rd in rdvms:
            tags = rd.get('tags') or []
            if tags:
                names = [t.get('name') for t in tags]
                tag_names.update(names)
                print(f'  - {rd.get("name")!r}: tags={names}')
        print(f'  distinct tag names seen: {sorted(tag_names)}')
    print()

    print('=== Total rdvm count (how big is the classification task) ===')
    r = gql(args.token, '{ rdvmsCount }')
    print(f'  {r}')
    print()

    # 8. "Visits / Provider" should only count completed visits where an exam was
    # performed (Megan's explicit correction) — not every encounter row regardless
    # of type/status. Encounter.visitType is a VisitType enum and Appointment has a
    # `status: AppointmentStatus` (per the `statuses: AppointmentStatus` arg on the
    # appointments root field) — need both enums' real values, plus a live sample
    # of recent encounters showing visitType/status/completedAt together, before
    # deciding what "completed + exam performed" means in terms of actual data.
    print('=== VisitType enum values ===')
    r = gql(args.token, '{ __type(name: "VisitType") { name enumValues { name } } }')
    data = (r.get('data') or {}).get('__type')
    print(f'  {[v["name"] for v in (data or {}).get("enumValues", [])] if data else "(not found)"}')
    print()

    print('=== AppointmentStatus enum values ===')
    r = gql(args.token, '{ __type(name: "AppointmentStatus") { name enumValues { name } } }')
    data = (r.get('data') or {}).get('__type')
    print(f'  {[v["name"] for v in (data or {}).get("enumValues", [])] if data else "(not found)"}')
    print()

    print('=== EncounterType fields ===')
    dump_type_fields(args.token, 'EncounterType')

    print('=== Live sample: last 30 days of encounters, visitType/status/encounterType/category tallies ===')
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=30)).isoformat() + 'T00:00:00'
    sample_query = '''
    query($s: NaiveDateTime, $limit: Int) {
      encounters(updatedAtStart: $s, limit: $limit) {
        id
        visitType
        category
        signedDatetime
        encounterType { id name }
        appointment { status completedAt startedAt }
      }
    }
    '''
    r = gql(args.token, sample_query, {'s': since, 'limit': 300})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('encounters') or []
        print(f'  fetched {len(rows)} encounters')
        status_counts, category_counts, enctype_counts, signed_counts = {}, {}, {}, {}
        for row in rows:
            appt = row.get('appointment') or {}
            st = appt.get('status')
            cat = row.get('category')
            et = (row.get('encounterType') or {}).get('name')
            signed = row.get('signedDatetime') is not None
            status_counts[st] = status_counts.get(st, 0) + 1
            category_counts[cat] = category_counts.get(cat, 0) + 1
            enctype_counts[et] = enctype_counts.get(et, 0) + 1
            signed_counts[signed] = signed_counts.get(signed, 0) + 1
        print(f'  appointment.status counts: {status_counts}')
        print(f'  category counts: {category_counts}')
        print(f'  encounterType.name counts: {enctype_counts}')
        print(f'  has signedDatetime counts: {signed_counts}')
    print()

    # 9. Geospatial mapping (illness/appointment/client maps) + Compliance Rate KPI:
    # Client.addresses: Address and Encounter.diagnostics: Diagnostic were both
    # confirmed to exist in a prior run, but neither Address nor Diagnostic itself
    # has ever been dumped (they don't match any KEYWORDS substring). Also found
    # PatientCompliance (productProtocols / protocolRemindersByProtocol) in passing
    # — that's the unconfirmed data source for the Compliance Rate KPI. Dumping all
    # three plus a live sample before designing anything geospatial or protocol-based.
    print('=== Address fields ===')
    dump_type_fields(args.token, 'Address')

    print('=== Diagnostic fields ===')
    dump_type_fields(args.token, 'Diagnostic')

    print('=== PatientCompliance fields ===')
    dump_type_fields(args.token, 'PatientCompliance')

    print('=== PatientProtocol fields ===')
    dump_type_fields(args.token, 'PatientProtocol')

    print('=== Live sample: first 20 clients with addresses ===')
    r = gql(args.token, '{ clients(limit: 20) { id name addresses { id line1 line2 city state postalCode country } } }')
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        clients = (r.get('data') or {}).get('clients') or []
        print(f'  fetched {len(clients)} clients')
        with_addr = [c for c in clients if c.get('addresses')]
        print(f'  {len(with_addr)}/{len(clients)} have at least one address')
        for c in with_addr[:5]:
            print(f'  - {c.get("name")!r}: {c.get("addresses")}')
    print()

    print('=== Live sample: last 30 days of encounters, diagnostics detail ===')
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=30)).isoformat() + 'T00:00:00'
    diag_query = '''
    query($s: NaiveDateTime, $limit: Int) {
      encounters(updatedAtStart: $s, limit: $limit) {
        id
        diagnostics { id name }
      }
    }
    '''
    r = gql(args.token, diag_query, {'s': since, 'limit': 100})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('encounters') or []
        with_diag = [row for row in rows if row.get('diagnostics')]
        print(f'  fetched {len(rows)} encounters, {len(with_diag)} have diagnostics')
        for row in with_diag[:8]:
            print(f'  - encounter {row["id"]}: {row.get("diagnostics")}')
    print()

    # 10. Real product category names for the Financial tab's "Revenue by Source"
    # breakdown, currently showing raw numeric product_category_id values
    # (Category 4949, Category 13598, ...) — checking whether Vetspire exposes a
    # ProductCategory type/root query with real names before assuming it doesn't.
    print('=== ProductCategory fields ===')
    dump_type_fields(args.token, 'ProductCategory')

    print('=== Root query fields matching "categor" ===')
    r = gql(args.token, '{ __schema { queryType { fields { name description } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    for f in fields:
        if 'categor' in f.get('name', '').lower():
            print(f'  ★ {f["name"]}: {f.get("description", "")}')
    print()

    print('=== Live sample: productCategories (no args — limit isn\'t a valid arg) ===')
    r = gql(args.token, '{ productCategories { id name } }')
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        cats = (r.get('data') or {}).get('productCategories') or []
        print(f'  fetched {len(cats)} categories')
        for c in cats:
            print(f'  - {c}')
    print()

    # 11. Geo-illness map: encounter_diagnostics/Diagnostic is confirmed to be
    # tests/procedures ORDERED, not a clinical diagnosis/condition — so before
    # assuming there's no structured illness data at all, scan every object
    # type name for diagnosis/problem/assessment/condition/soap-note vocabulary
    # (KEYWORDS above never included these), and dump the full Encounter type's
    # own fields (only EncounterType, the template, has been dumped so far —
    # not Encounter, the actual visit record).
    print('=== Object type names matching illness/diagnosis vocabulary ===')
    ILLNESS_KEYWORDS = ['diagnos', 'assess', 'problem', 'condition', 'illness', 'soap', 'note', 'medical', 'history']
    r = gql(args.token, '{ __schema { types { name kind } } }')
    types = (r.get('data') or {}).get('__schema', {}).get('types', [])
    matches = [t for t in types if t['kind'] == 'OBJECT' and any(k in t['name'].lower() for k in ILLNESS_KEYWORDS)]
    for t in matches:
        print(f'  ★ {t["name"]}')
    if not matches:
        print('  (none)')
    print()

    print('=== Encounter fields (the visit record itself, not EncounterType) ===')
    dump_type_fields(args.token, 'Encounter')

    # 12. Encounter.problems: Problem is a direct field on the encounter record
    # (distinct from diagnostics: Diagnostic, confirmed tests/procedures ordered)
    # -- most likely candidate for the actual clinical diagnosis/illness this
    # gets asked for over and over (geo-illness map, "determined illness").
    # Dumping Problem's own fields plus a live sample before assuming its shape.
    print('=== Problem fields ===')
    dump_type_fields(args.token, 'Problem')

    print('=== Live sample: last 30 days of encounters, problems detail ===')
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=30)).isoformat() + 'T00:00:00'
    problem_query = '''
    query($s: NaiveDateTime, $limit: Int) {
      encounters(updatedAtStart: $s, limit: $limit) {
        id
        problems { id name }
      }
    }
    '''
    r = gql(args.token, problem_query, {'s': since, 'limit': 100})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('encounters') or []
        with_problems = [row for row in rows if row.get('problems')]
        print(f'  fetched {len(rows)} encounters, {len(with_problems)} have problems')
        for row in with_problems[:15]:
            print(f'  - encounter {row["id"]}: {row.get("problems")}')
    print()

    # 13. 0/100 recent encounters had any problems attached via
    # encounter.problems -- before concluding the Problem list feature is
    # simply unused at this practice, check two other explanations: (a) a
    # much wider window (180d) in case problems attach only to older,
    # already-resolved conditions, not this month's visits, and (b) Patient
    # itself might expose problems as the patient's whole-chart problem
    # list, independent of any one encounter, which the encounter-scoped
    # query above would never surface.
    print('=== Patient fields ===')
    dump_type_fields(args.token, 'Patient')

    print('=== Live sample: last 180 days of encounters, problems detail ===')
    since_180 = (date.today() - timedelta(days=180)).isoformat() + 'T00:00:00'
    r = gql(args.token, problem_query, {'s': since_180, 'limit': 300})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('encounters') or []
        with_problems = [row for row in rows if row.get('problems')]
        print(f'  fetched {len(rows)} encounters, {len(with_problems)} have problems')
        for row in with_problems[:15]:
            print(f'  - encounter {row["id"]}: {row.get("problems")}')
    print()

    print('=== Live sample: first 20 patients, problems via patient (not encounter) ===')
    patient_query = '{ patients(limit: 20) { id species problems { id name isActive onsetDate } } }'
    r = gql(args.token, patient_query)
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('patients') or []
        with_problems = [row for row in rows if row.get('problems')]
        print(f'  fetched {len(rows)} patients, {len(with_problems)} have problems')
        for row in with_problems[:10]:
            print(f'  - patient {row["id"]} ({row.get("species")}): {row.get("problems")}')
    print()

    # 14. Problem (the chronic problem-list feature) is confirmed completely
    # unused: 0/300 encounters over 180 days, 0/20 patients sampled. But
    # Patient exposes a SEPARATE field, patientDiagnoses: PatientDiagnosis,
    # never checked -- likely the actual day-to-day diagnosis record staff
    # enter per visit, distinct from the optional long-term Problem tracker
    # many practices skip. Also dumping Diagnosis (referenced by
    # Problem.diagnosis) since it may be the same underlying illness-name
    # type reused there.
    print('=== PatientDiagnosis fields ===')
    dump_type_fields(args.token, 'PatientDiagnosis')

    print('=== Diagnosis fields ===')
    dump_type_fields(args.token, 'Diagnosis')

    print('=== Live sample: first 20 patients, patientDiagnoses ===')
    pd_query = '{ patients(limit: 20) { id species patientDiagnoses { id } } }'
    r = gql(args.token, pd_query)
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('patients') or []
        with_pd = [row for row in rows if row.get('patientDiagnoses')]
        print(f'  fetched {len(rows)} patients, {len(with_pd)} have patientDiagnoses')
        for row in with_pd[:10]:
            print(f'  - patient {row["id"]} ({row.get("species")}): {row.get("patientDiagnoses")}')
    print()

    # 15. encounters.chief_complaint has been a column in the schema since
    # the original migration but has NEVER actually been populated by any
    # sync -- no field in vetspire_clinical_sync.py or this probe's own
    # Encounter field dump maps to it (Encounter has no chiefComplaint
    # field at all). appointmentReasonCategories turned up earlier as a
    # root query field matching "categor" -- checking Appointment's own
    # fields (never dumped) plus root fields matching "reason" to find
    # where reason-for-visit data actually lives before building anything
    # on chief_complaint as populated data it never was.
    print('=== Appointment fields ===')
    dump_type_fields(args.token, 'Appointment')

    print('=== AppointmentReasonCategory fields ===')
    dump_type_fields(args.token, 'AppointmentReasonCategory')

    print('=== Root query fields matching "reason" ===')
    r = gql(args.token, '{ __schema { queryType { fields { name description } } } }')
    fields = (r.get('data') or {}).get('__schema', {}).get('queryType', {}).get('fields', [])
    for f in fields:
        if 'reason' in f.get('name', '').lower():
            print(f'  ★ {f["name"]}: {f.get("description", "")}')
    print()

    print('=== Live sample: last 30 days of encounters, appointment reason detail ===')
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=30)).isoformat() + 'T00:00:00'
    # reasonCategory's field names are unknown until the dump above runs --
    # only request "id" here (present on virtually every GraphQL object
    # type) rather than guessing at "name" again.
    reason_query = '''
    query($s: NaiveDateTime, $limit: Int) {
      encounters(updatedAtStart: $s, limit: $limit) {
        id
        title
        appointment { id reason reasonCategory { id } }
      }
    }
    '''
    r = gql(args.token, reason_query, {'s': since, 'limit': 300})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        rows = (r.get('data') or {}).get('encounters') or []
        with_reason = [row for row in rows if (row.get('appointment') or {}).get('reason')]
        with_category = [row for row in rows if (row.get('appointment') or {}).get('reasonCategory')]
        print(f'  fetched {len(rows)} encounters, {len(with_reason)} have appointment.reason, '
              f'{len(with_category)} have appointment.reasonCategory')
        for row in with_reason[:20]:
            appt = row.get('appointment') or {}
            print(f'  - encounter {row["id"]}: reason={appt.get("reason")!r} '
                  f'category_id={(appt.get("reasonCategory") or {}).get("id")!r} title={row.get("title")!r}')
    print()

    # 16. The case-dollar-value heatmap (scoutsync_case_maps_and_heatmaps.sql's
    # v_case_heatmap) turned out to always compute case_value=0 in production:
    # invoice_line_items is written by vetspire_financial_sync.py from
    # salesReport, which only returns day-level totals broken down by
    # provider/product-category -- encounter_id is never set on those rows
    # because salesReport has no per-encounter granularity, so the view's
    # `join invoice_line_items on encounter_id = encounters.id` never matches
    # anything. ReportBreakdown's enum (dumped in an earlier run) includes
    # APPOINTMENT_TIME -- checking here whether that breakdown actually
    # returns a real per-appointment timestamp (which would let the dashboard
    # compute day-of-week/hour-of-day directly from salesReport, no encounter
    # join needed) or just another coarse bucket like the DAY segment did.
    print('=== salesReport with APPOINTMENT_TIME breakdown (real row shape, not guessed) ===')
    at_query = '''
    query($lids:[ID!], $s:Date, $e:Date){
        salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                    breakdowns:[APPOINTMENT_TIME])
    }
    '''
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    r = gql(args.token, at_query, {'lids': ['28253'], 's': week_ago, 'e': yesterday})
    if 'errors' in r:
        print(f'  ERROR: {r["errors"]}')
    else:
        raw = r.get('data', {}).get('salesReport', '[]')
        rows = json.loads(raw) if isinstance(raw, str) else (raw or [])
        print(f'  {len(rows)} rows over {week_ago}..{yesterday}')
        for row in rows[:10]:
            print(f'  - {row}')
    print()

    print('=== salesReport with APPOINTMENT_TIME + PROVIDER_ID breakdown (paired, for comparison) ===')
    at2_query = '''
    query($lids:[ID!], $s:Date, $e:Date){
        salesReport(locationIds:$lids, startDate:$s, endDate:$e,
                    breakdowns:[APPOINTMENT_TIME, PROVIDER_ID])
    }
    '''
    r2 = gql(args.token, at2_query, {'lids': ['28253'], 's': week_ago, 'e': yesterday})
    if 'errors' in r2:
        print(f'  ERROR: {r2["errors"]}')
    else:
        raw2 = r2.get('data', {}).get('salesReport', '[]')
        rows2 = json.loads(raw2) if isinstance(raw2, str) else (raw2 or [])
        print(f'  {len(rows2)} rows over {week_ago}..{yesterday}')
        for row in rows2[:10]:
            print(f'  - {row}')
    print()

    # 17. salesReport flatly rejects APPOINTMENT_TIME despite it appearing in
    # ReportBreakdown's enum values (confirmed: 'unprocessable_entity', only
    # LOCATION_ID/PROVIDER_ID/REVENUE_CENTER_ID/PRODUCT_TYPE_ID/
    # PRODUCT_CATEGORY_ID/PRODUCT_ID/DEPARTMENT_ID/CLIENT_ID/PAYROLL_ID/
    # RDVM_ID are actually supported) -- and ReportSegment's smallest unit is
    # DAY (confirmed in an earlier run), so salesReport has no time-of-day
    # dimension at all, full stop. The only other candidate for a real
    # per-encounter dollar figure is Encounter.encounterProducts.product --
    # EncounterProduct itself has no price field, only `quantity` and a
    # nested `product`, so checking Product's fields for whatever the real
    # sale-price field is called (unitCost, dumped previously for inventory
    # tracking, is cost basis, not what a client is charged).
    print('=== Product fields ===')
    dump_type_fields(args.token, 'Product')

    print('=== Live sample: encounterProducts with product pricing (field name from the dump above) ===')
    r = gql(args.token, '{ __type(name: "Product") { fields { name type { name kind ofType { name } } } } }')
    prod_fields = {f['name']: f for f in ((r.get('data') or {}).get('__type') or {}).get('fields', [])}
    price_field = next((n for n in prod_fields if n.lower() in
                        ('price', 'unitprice', 'retailprice', 'saleprice', 'sellprice', 'listprice')), None)
    if not price_field:
        print(f'  (no obvious price field on Product -- got: {sorted(prod_fields)})')
    else:
        print(f'  using product.{price_field}')
        ep_query = f'''
        query($s: NaiveDateTime, $limit: Int) {{
          encounters(updatedAtStart: $s, limit: $limit) {{
            id
            start
            encounterProducts {{ name quantity product {{ id name {price_field} }} }}
          }}
        }}
        '''
        r2 = gql(args.token, ep_query, {'s': week_ago + 'T00:00:00', 'limit': 30})
        if 'errors' in r2:
            print(f'  ERROR: {r2["errors"]}')
        else:
            rows3 = (r2.get('data') or {}).get('encounters') or []
            with_products = [row for row in rows3 if row.get('encounterProducts')]
            print(f'  fetched {len(rows3)} encounters, {len(with_products)} have encounterProducts')
            for row in with_products[:8]:
                print(f'  - encounter {row["id"]} ({row.get("start")}): {row.get("encounterProducts")}')
    print()


if __name__ == '__main__':
    main()
