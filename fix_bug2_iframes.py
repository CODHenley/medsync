import sys
import os

BASE = '/Users/meganhenley/Downloads/medsync_deploy'

LISTENER = (
    "\nwindow.addEventListener('message', function(e) {\n"
    "  if (!e.data || e.data.type !== 'setLocation') return;\n"
    "  window._pendingLocation = e.data.loc;\n"
    "  var sel = document.getElementById('loc-select');\n"
    "  if (!sel || sel.options.length <= 1) return;\n"
    "  for (var i = 0; i < sel.options.length; i++) {\n"
    "    if (sel.options[i].text === e.data.loc) {\n"
    "      sel.value = sel.options[i].value;\n"
    "      onLocChange();\n"
    "      break;\n"
    "    }\n"
    "  }\n"
    "});\n"
    "</script>"
)

patches = [
    {
        'file': 'medsync_weekly_order_live.html',
        'loc_old': (
            "  if (locs.length) {\n"
            "    sel.value = locs[0].id;\n"
            "    state.locationId = locs[0].id;\n"
            "    state.locationName = locs[0].name;\n"
            "    await loadProducts();\n"
            "  }"
        ),
        'loc_new': (
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
    },
    {
        'file': 'medsync_receiving_live.html',
        'loc_old': (
            "  if (locs.length) {\n"
            "    sel.value = locs[0].id;\n"
            "    state.locationId = locs[0].id;\n"
            "    state.locationName = locs[0].name;\n"
            "    await loadOrders();\n"
            "  }"
        ),
        'loc_new': (
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
    },
    {
        'file': 'medsync_goods_lost_live.html',
        'loc_old': (
            "  if (locs.length) {\n"
            "    sel.value = locs[0].id;\n"
            "    state.locationId = locs[0].id;\n"
            "    state.locationName = locs[0].name;\n"
            "    document.getElementById('tb-loc').textContent = 'Log goods lost · ' + locs[0].name;\n"
            "    await loadHistory();\n"
            "  }"
        ),
        'loc_new': (
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
    },
]

errors = []
for p in patches:
    path = os.path.join(BASE, p['file'])
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    # Check loc patch
    if p['loc_old'] not in src:
        errors.append(f"ERROR [{p['file']}]: loadLocations target not found.")
        continue
    if src.count(p['loc_old']) > 1:
        errors.append(f"ERROR [{p['file']}]: loadLocations target found multiple times.")
        continue

    # Check listener not already added
    if '_pendingLocation' in src:
        errors.append(f"SKIP [{p['file']}]: already patched.")
        continue

    patched = src.replace(p['loc_old'], p['loc_new'], 1)
    patched = patched.replace('</script>', LISTENER, 1)  # inject before first </script>

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f"OK: {p['file']} patched.")

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

print("All three iframe files patched successfully.")
