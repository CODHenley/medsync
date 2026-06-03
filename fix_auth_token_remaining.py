import sys
import os

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

SESS_LINE = "const _sess = (function(){ try { return JSON.parse(localStorage.getItem('medsync_session') || '{}'); } catch(e) { return {}; } })();\n"

patches = [
    {
        'file': 'medsync_activity_log_live.html',
        'old': "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY };",
        'new': SESS_LINE + "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + (_sess.access_token || SUPA_KEY) };",
    },
    {
        'file': 'medsync_lot_lifecycle_live.html',
        'old': "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY };",
        'new': SESS_LINE + "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + (_sess.access_token || SUPA_KEY) };",
    },
    {
        'file': 'medsync_hospital_receiver_live.html',
        'old': "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY, 'Content-Type': 'application/json' };",
        'new': SESS_LINE + "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + (_sess.access_token || SUPA_KEY), 'Content-Type': 'application/json' };",
    },
    {
        'file': 'medsync_analytics_live.html',
        'old': "  'Authorization': 'Bearer ' + SUPA_KEY,",
        'new': "  'Authorization': 'Bearer ' + (function(){ try { return JSON.parse(localStorage.getItem('medsync_session') || '{}').access_token || SUPA_KEY; } catch(e) { return SUPA_KEY; } })(),",
    },
]

errors = []
for p in patches:
    path = os.path.join(BASE, p['file'])
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    if p['old'] not in src:
        errors.append(f"ERROR [{p['file']}]: target not found.")
        continue
    if src.count(p['old']) > 1:
        errors.append(f"ERROR [{p['file']}]: target found multiple times.")
        continue

    patched = src.replace(p['old'], p['new'], 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f"OK: {p['file']}")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

print("All 4 files patched.")
