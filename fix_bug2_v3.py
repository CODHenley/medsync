import sys
import os

BASE = '/Users/meganhenley/Downloads/medsync_deploy'

# Replace the localStorage block (from v2) with one that handles
# both shapes Supabase can return for locations:
#   array:  locations: [{name: "Old Orchard"}]  -> locations[0].name
#   object: locations: {name: "Old Orchard"}    -> locations.name

LOC_READ = (
    "    var _mu = {};\n"
    "    try { _mu = JSON.parse(localStorage.getItem('medsync_user') || '{}'); } catch(e) {}\n"
    "    var _locName = null;\n"
    "    if (_mu.role === 'manager' && _mu.locations) {\n"
    "      if (Array.isArray(_mu.locations) && _mu.locations[0]) {\n"
    "        _locName = _mu.locations[0].name;\n"
    "      } else if (_mu.locations.name) {\n"
    "        _locName = _mu.locations.name;\n"
    "      }\n"
    "    }\n"
)

OLD_LOC_READ = (
    "    var _mu = {};\n"
    "    try { _mu = JSON.parse(localStorage.getItem('medsync_user') || '{}'); } catch(e) {}\n"
    "    var _locName = (_mu.role === 'manager' && _mu.locations && _mu.locations[0]) ? _mu.locations[0].name : null;\n"
)

patches = [
    'medsync_weekly_order_live.html',
    'medsync_receiving_live.html',
    'medsync_goods_lost_live.html',
]

errors = []
for fname in patches:
    path = os.path.join(BASE, fname)
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    if OLD_LOC_READ not in src:
        errors.append(f"ERROR [{fname}]: target not found.")
        continue
    if src.count(OLD_LOC_READ) > 1:
        errors.append(f"ERROR [{fname}]: target found multiple times.")
        continue

    patched = src.replace(OLD_LOC_READ, LOC_READ, 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f"OK: {fname} patched.")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

print("Done. Deploy and hard-reload (Cmd+Shift+R) to test.")
