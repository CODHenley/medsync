import sys

path = '/sessions/peaceful-confident-bell/mnt/medsync_deploy/medsync_goods_lost_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Make activity_log insert fire-and-forget (can't block success screen)
OLD_ACTLOG = (
    "    // Log to activity_log\n"
    "    await fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'goods',\n"
    "        description:  'Goods lost entry submitted',\n"
    "        flag:         'ok',\n"
    "        metadata: {\n"
    "          category: state.category,\n"
    "          product: state.productName,\n"
    "          value: valueLost,\n"
    "          qty: state.qty\n"
    "        }\n"
    "      })\n"
    "    });"
)

NEW_ACTLOG = (
    "    // Log to activity_log (fire-and-forget — never blocks success screen)\n"
    "    fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'goods',\n"
    "        description:  'Goods lost entry submitted',\n"
    "        flag:         'ok',\n"
    "        metadata: {\n"
    "          category: state.category,\n"
    "          product: state.productName,\n"
    "          value: valueLost,\n"
    "          qty: state.qty\n"
    "        }\n"
    "      })\n"
    "    }).catch(() => {});"
)

# 2. Fix value_lost stored in DB to use per-unit cost (not package price)
OLD_VAL = "  const valueLost = (state.productPrice || 0) * state.qty;"
NEW_VAL = (
    "  const _pkgSize = state.productPkgSize || 1;\n"
    "  const valueLost = ((state.productPrice || 0) / _pkgSize) * state.qty;"
)

errors = []
for old, new, desc in [
    (OLD_ACTLOG, NEW_ACTLOG, 'activity_log fire-and-forget'),
    (OLD_VAL, NEW_VAL, 'value_lost per-unit calculation'),
]:
    if old not in src:
        errors.append(f'ERROR: target not found — {desc}')
    elif src.count(old) > 1:
        errors.append(f'ERROR: target found multiple times — {desc}')
    else:
        src = src.replace(old, new, 1)

if errors:
    for e in errors:
        print(e)
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: submitLoss patched — activity_log is now fire-and-forget, value_lost uses per-unit cost.")
