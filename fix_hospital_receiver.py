import sys

path = '/sessions/peaceful-confident-bell/mnt/medsync_deploy/medsync_hospital_receiver_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Make activity_log fire-and-forget in hrComplete
OLD_ACTLOG_COMPLETE = (
    "    // Log activity\n"
    "    await fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'receive',\n"
    "        description:  'Receiving session completed',\n"
    "        reference_id: state.selectedOrder.ref,\n"
    "        flag:         'ok',\n"
    "        metadata: { received_by: state.name, skus: confirmed.length }\n"
    "      })\n"
    "    });"
)
NEW_ACTLOG_COMPLETE = (
    "    // Log activity (fire-and-forget)\n"
    "    fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'receive',\n"
    "        description:  'Receiving session completed',\n"
    "        reference_id: state.selectedOrder.ref,\n"
    "        flag:         'ok',\n"
    "        metadata: { received_by: state.name, skus: confirmed.length }\n"
    "      })\n"
    "    }).catch(() => {});"
)

# 2. Make activity_log fire-and-forget in hrLogGoods
OLD_ACTLOG_GOODS = (
    "    await fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'goods',\n"
    "        description:  'Goods lost entry submitted',\n"
    "        flag:         'ok',\n"
    "        metadata: { category, submitted_by: state.name }\n"
    "      })\n"
    "    });"
)
NEW_ACTLOG_GOODS = (
    "    fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "      method: 'POST',\n"
    "      headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "      body: JSON.stringify({\n"
    "        location_id:  state.locationId,\n"
    "        event_type:   'goods',\n"
    "        description:  'Goods lost entry submitted',\n"
    "        flag:         'ok',\n"
    "        metadata: { category, submitted_by: state.name }\n"
    "      })\n"
    "    }).catch(() => {});"
)

# 3. Fix hardcoded expiration date — use lot scan data or default to 1 year out
OLD_EXP = "          expiration_date: '2027-06-01',"
NEW_EXP = "          expiration_date: line.expDate || new Date(new Date().setFullYear(new Date().getFullYear()+1)).toISOString().split('T')[0],"

errors = []
for old, new, desc in [
    (OLD_ACTLOG_COMPLETE, NEW_ACTLOG_COMPLETE, 'activity_log fire-and-forget in hrComplete'),
    (OLD_ACTLOG_GOODS, NEW_ACTLOG_GOODS, 'activity_log fire-and-forget in hrLogGoods'),
    (OLD_EXP, NEW_EXP, 'hardcoded expiration date'),
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

print("OK: medsync_hospital_receiver_live.html patched.")
