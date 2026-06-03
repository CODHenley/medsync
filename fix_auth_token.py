import sys
import os

BASE = '/Users/meganhenley/Downloads/medsync_deploy'

OLD = "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY, 'Content-Type': 'application/json' };"

NEW = (
    "const _sess = (function(){ try { return JSON.parse(localStorage.getItem('medsync_session') || '{}'); } catch(e) { return {}; } })();\n"
    "const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + (_sess.access_token || SUPA_KEY), 'Content-Type': 'application/json' };"
)

files = [
    'medsync_weekly_order_live.html',
    'medsync_receiving_live.html',
    'medsync_goods_lost_live.html',
]

errors = []
for fname in files:
    path = os.path.join(BASE, fname)
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    if OLD not in src:
        errors.append(f"ERROR [{fname}]: target not found.")
        continue
    if src.count(OLD) > 1:
        errors.append(f"ERROR [{fname}]: target found multiple times.")
        continue

    patched = src.replace(OLD, NEW, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f"OK: {fname} patched.")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

print("Done. Deploy and hard-reload to test.")
