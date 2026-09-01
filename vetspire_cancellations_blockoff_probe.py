#!/usr/bin/env python3
"""
One-off: verify two things live against production Vetspire before building
on top of them --
(1) the appointments() query actually returns deleted/cancelled appointment
    records with deletedBy/deletionReason/status populated (for a new
    Cancellations & Deletions operations report)
(2) block-off schedule entries (AppointmentType.isBlockoff) actually exist
    and are queryable with a real start/duration, tied to a provider/location
    (for a schedule-block-based partial-closure signal)

Uses Lincoln Park + the known Oct 17 2025 date (already confirmed to have
real cancellations/deletions for Dr. Aria Hill) as the test case, plus a
wider recent window to see if blockoffs show up anywhere at all.
"""
import argparse, json, urllib.request, urllib.error

VETSPIRE_URL = 'https://api.vetspire.com/graphql'
LP_ID = "23083"


def gql(token, query, variables=None):
    payload = json.dumps({'query': query, 'variables': variables or {}}).encode()
    req = urllib.request.Request(
        VETSPIRE_URL, data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    args = parser.parse_args()
    token = args.token.strip().removeprefix('Bearer ').strip()

    print("=== (1) Deleted/cancelled appointments at Lincoln Park, Oct 17 2025 ===")
    q1 = """
    query($locationId: ID, $start: DateTime, $end: DateTime) {
      appointments(locationId: $locationId, start: $start, end: $end, includeDeleted: true, limit: 50) {
        id
        status
        deleted
        deletedBy { id name }
        deletionReason
        provider { id name }
        patient { id }
        start
        duration
        insertedAt
        updatedAt
        type { name isBlockoff }
      }
    }
    """
    r1 = gql(token, q1, {"locationId": LP_ID, "start": "2025-10-17T00:00:00Z", "end": "2025-10-18T00:00:00Z"})
    print(json.dumps(r1, indent=2)[:6000])

    print("\n=== (2) Any block-off appointments at Lincoln Park in the last 60 days ===")
    q2 = """
    query($locationId: ID, $start: DateTime, $end: DateTime) {
      appointments(locationId: $locationId, start: $start, end: $end, includeDeleted: true, limit: 200) {
        id
        start
        duration
        deleted
        provider { id name }
        type { name isBlockoff }
      }
    }
    """
    r2 = gql(token, q2, {"locationId": LP_ID, "start": "2026-07-01T00:00:00Z", "end": "2026-09-01T00:00:00Z"})
    appts = (r2.get("data") or {}).get("appointments") or []
    blockoffs = [a for a in appts if (a.get("type") or {}).get("isBlockoff")]
    print(f"Total appointments in window: {len(appts)}")
    print(f"Blockoff appointments found: {len(blockoffs)}")
    if "errors" in r2:
        print("ERRORS:", r2["errors"])

    print("\n=== (3) Distinct block-off type names, with count and duration range ===")
    from collections import defaultdict
    by_type = defaultdict(list)
    for b in blockoffs:
        by_type[b['type']['name']].append(b.get('duration') or 0)
    for tname, durations in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tname!r}: count={len(durations)} duration_min={min(durations)} duration_max={max(durations)} duration_avg={sum(durations)/len(durations):.0f}")

    print("\n=== (4) Sample of longest-duration blockoffs (candidates for real closures) ===")
    longest = sorted(blockoffs, key=lambda b: -(b.get('duration') or 0))[:15]
    for b in longest:
        print(f"  start={b['start']} duration={b['duration']} provider={(b.get('provider') or {}).get('name')} type={b['type']['name']}")


if __name__ == '__main__':
    main()
