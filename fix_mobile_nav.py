"""
Fix mobile nav overlap — 3-part fix:
1. index.html: push iframe screen containers DOWN by 48px (margin-top: 48px) so they
   start below the fixed nav, not underneath it.
2. Each iframe file: REMOVE the internal padding-top that was trying to compensate
   (now that the iframe is correctly positioned, no internal offset is needed).
3. Hospital receiver: same — remove the JS paddingTop on #app.

This replaces the failed CSS/JS padding approach inside the iframes.
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# ── 1. index.html ────────────────────────────────────────────────────────────

with open(f'{BASE}/index.html', 'r', encoding='utf-8') as f:
    src = f.read()

FINAL_CSS = """
/* ── FINAL: iframe screens start below fixed nav ────────────── */
@media (max-width: 768px) {
  #ms-analytics, #ms-lifecycle, #ms-actlog, #ms-receiver {
    margin-top: 48px !important;
  }
}
"""

target = '</style>\n</head>'
if target not in src:
    # try variant
    target = '</style>\n\n</head>'

if target not in src:
    print('ERROR: cannot locate </style> end in index.html')
else:
    src = src.replace(target, FINAL_CSS + target, 1)
    with open(f'{BASE}/index.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK: index.html — added margin-top:48px for iframe screens')

# ── 2. Analytics, Lifecycle, Activity Log — remove internal padding ──────────

IFRAME_FILES = [
    'medsync_analytics_live.html',
    'medsync_lot_lifecycle_live.html',
    'medsync_activity_log_live.html',
]

OLD_CSS = '  .right, .main-area { padding-top: 48px !important; box-sizing: border-box !important; }'
NEW_CSS = '  .right, .main-area { padding-top: 0 !important; box-sizing: border-box !important; }'

OLD_JS  = "        mainArea.style.paddingTop = '52px';"
NEW_JS  = "        mainArea.style.paddingTop = '0';"

for fname in IFRAME_FILES:
    path = f'{BASE}/{fname}'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    ok = []
    if OLD_CSS in content:
        content = content.replace(OLD_CSS, NEW_CSS, 1)
        ok.append('CSS padding-top')
    if OLD_JS in content:
        content = content.replace(OLD_JS, NEW_JS, 1)
        ok.append('JS paddingTop')

    if ok:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'OK: {fname} — removed {", ".join(ok)}')
    else:
        print(f'WARNING: {fname} — no matches found (already clean?)')

# ── 3. Hospital Receiver — remove JS paddingTop on #app ─────────────────────

RECV = f'{BASE}/medsync_hospital_receiver_live.html'
with open(RECV, 'r', encoding='utf-8') as f:
    recv = f.read()

# Also remove the CSS .shell { padding-top: 48px } rule
OLD_RECV_CSS = '@media (max-width: 768px) { .shell { padding-top: 48px !important; box-sizing: border-box !important; } }'
NEW_RECV_CSS = '/* mobile nav offset handled by parent (margin-top on #ms-receiver) */'

OLD_RECV_JS_BLOCK = (
    '  if (window.self !== window.top && window.innerWidth <= 768) {\n'
    "    var shell = document.getElementById('app');\n"
    "    if (shell) shell.style.paddingTop = '52px';\n"
    "    document.body.style.paddingTop = '0';\n"
    '  }'
)
NEW_RECV_JS_BLOCK = '  // mobile nav offset handled by parent index.html'

changed = []
if OLD_RECV_CSS in recv:
    recv = recv.replace(OLD_RECV_CSS, NEW_RECV_CSS, 1)
    changed.append('CSS .shell padding-top')
if OLD_RECV_JS_BLOCK in recv:
    recv = recv.replace(OLD_RECV_JS_BLOCK, NEW_RECV_JS_BLOCK, 1)
    changed.append('JS paddingTop block')

if changed:
    with open(RECV, 'w', encoding='utf-8') as f:
        f.write(recv)
    print(f'OK: medsync_hospital_receiver_live.html — removed {", ".join(changed)}')
else:
    print('WARNING: hospital receiver — no matches (check manually)')
