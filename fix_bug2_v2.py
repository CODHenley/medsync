import sys
import os

BASE = '/Users/meganhenley/Downloads/medsync_deploy'

# Each file: replace the loadLocations default-selection block
# with one that reads medsync_user from localStorage directly.
# No postMessage timing issues — same domain, shared localStorage.

patches = [
    {
        'file': 'medsync_weekly_order_live.html',
        'old': (
            "  if (locs.length) {\n"
            "    const _target = window._pendingLocation;\n"
            "    const _match = _target ? locs.find(l => l.name === _target) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    await loadProducts();\n"
            "  }"
        ),
        'new': (
            "  if (locs.length) {\n"
            "    var _mu = {};\n"
            "    try { _mu = JSON.parse(localStorage.getItem('medsync_user') || '{}'); } catch(e) {}\n"
            "    var _locName = (_mu.role === 'manager' && _mu.locations && _mu.locations[0]) ? _mu.locations[0].name : null;\n"
            "    const _match = _locName ? locs.find(l => l.name === _locName) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    await loadProducts();\n"
            "  }"
        ),
    },
    {
        'file': 'medsync_receiving_live.html',
        'old': (
            "  if (locs.length) {\n"
            "    const _target = window._pendingLocation;\n"
            "    const _match = _target ? locs.find(l => l.name === _target) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    await loadOrders();\n"
            "  }"
        ),
        'new': (
            "  if (locs.length) {\n"
            "    var _mu = {};\n"
            "    try { _mu = JSON.parse(localStorage.getItem('medsync_user') || '{}'); } catch(e) {}\n"
            "    var _locName = (_mu.role === 'manager' && _mu.locations && _mu.locations[0]) ? _mu.locations[0].name : null;\n"
            "    const _match = _locName ? locs.find(l => l.name === _locName) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    await loadOrders();\n"
            "  }"
        ),
    },
    {
        'file': 'medsync_goods_lost_live.html',
        'old': (
            "  if (locs.length) {\n"
            "    const _target = window._pendingLocation;\n"
            "    const _match = _target ? locs.find(l => l.name === _target) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    document.getElementById('tb-loc').textContent = 'Log goods lost · ' + _loc.name;\n"
            "    await loadHistory();\n"
            "  }"
        ),
        'new': (
            "  if (locs.length) {\n"
            "    var _mu = {};\n"
            "    try { _mu = JSON.parse(localStorage.getItem('medsync_user') || '{}'); } catch(e) {}\n"
            "    var _locName = (_mu.role === 'manager' && _mu.locations && _mu.locations[0]) ? _mu.locations[0].name : null;\n"
            "    const _match = _locName ? locs.find(l => l.name === _locName) : null;\n"
            "    const _loc = _match || locs[0];\n"
            "    sel.value = _loc.id;\n"
            "    state.locationId = _loc.id;\n"
            "    state.locationName = _loc.name;\n"
            "    document.getElementById('tb-loc').textContent = 'Log goods lost · ' + _loc.name;\n"
            "    await loadHistory();\n"
            "  }"
        ),
    },
]

errors = []
for p in patches:
    path = os.path.join(BASE, p['file'])
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    if p['old'] not in src:
        errors.append(f"ERROR [{p['file']}]: target not found — already patched or mismatch.")
        continue
    if src.count(p['old']) > 1:
        errors.append(f"ERROR [{p['file']}]: target found multiple times.")
        continue

    patched = src.replace(p['old'], p['new'], 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f"OK: {p['file']} patched.")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

print("All three files patched. Deploy and hard-reload to test.")
