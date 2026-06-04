import sys, os

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# Fix A: Analytics, Lot Lifecycle, Activity Log
# Add mobile override AFTER global iframe section so it wins the cascade
MOBILE_OVERRIDE = (
    "\n@media (max-width: 768px) {\n"
    "  html { height: auto !important; overflow: auto !important; overflow-x: hidden !important; }\n"
    "  body { height: auto !important; overflow: auto !important; overflow-x: hidden !important; min-height: 100% !important; }\n"
    "  .right, .main-area { height: auto !important; overflow: visible !important; }\n"
    "}\n"
)

files_a = [
    'medsync_analytics_live.html',
    'medsync_lot_lifecycle_live.html',
    'medsync_activity_log_live.html',
]

ANCHOR = '/* ── Fit iframe exactly — no gap ────────────────────────────── */'

for fname in files_a:
    path = os.path.join(BASE, fname)
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    if ANCHOR not in src:
        print(f'ERROR [{fname}]: anchor not found')
        continue
    if 'height: auto !important; overflow: auto' in src:
        print(f'SKIP [{fname}]: already patched')
        continue
    patched = src.replace(ANCHOR, ANCHOR + MOBILE_OVERRIDE, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print(f'OK: {fname}')

# Fix C: Hospital Receiver (same anchor)
hr_path = os.path.join(BASE, 'medsync_hospital_receiver_live.html')
with open(hr_path, 'r', encoding='utf-8') as f:
    src = f.read()
if ANCHOR not in src:
    print('ERROR [hospital_receiver]: anchor not found')
elif 'height: auto !important; overflow: auto' in src:
    print('SKIP [hospital_receiver]: already patched')
else:
    patched = src.replace(ANCHOR, ANCHOR + MOBILE_OVERRIDE, 1)
    with open(hr_path, 'w', encoding='utf-8') as f:
        f.write(patched)
    print('OK: medsync_hospital_receiver_live.html')

print('Fix A+C done.')
