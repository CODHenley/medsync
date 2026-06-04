"""
Two fixes:
1. Hospital Receiver: scan buttons overflow right on mobile — reduce btn-scan padding
2. Goods Lost: add "Thank you, [name]!" to the success screen
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# ── 1. Hospital Receiver: compact scan buttons on mobile ─────────────────────

RECV = f'{BASE}/medsync_hospital_receiver_live.html'
with open(RECV, 'r', encoding='utf-8') as f:
    recv = f.read()

OLD_RECV_CSS = '/* mobile nav offset handled by parent (margin-top on #ms-receiver) */'
NEW_RECV_CSS = '''/* mobile nav offset handled by parent (margin-top on #ms-receiver) */
@media (max-width: 768px) {
  .scan-input-wrap { gap: 6px !important; }
  .btn-scan { padding: 10px 12px !important; font-size: 12px !important; min-width: 0 !important; }
}'''

if OLD_RECV_CSS in recv:
    recv = recv.replace(OLD_RECV_CSS, NEW_RECV_CSS, 1)
    with open(RECV, 'w', encoding='utf-8') as f:
        f.write(recv)
    print('OK: hospital receiver — compact scan buttons on mobile')
else:
    print('ERROR: hospital receiver target not found')

# ── 2. Goods Lost: add Thank you message to success screen ───────────────────

GL = f'{BASE}/medsync_goods_lost_live.html'
with open(GL, 'r', encoding='utf-8') as f:
    gl = f.read()

# Add a thank-you div to the success HTML
OLD_SUCCESS_HTML = (
    '    <div class="success-icon">✓</div>\n'
    '    <div class="success-title">Loss logged</div>\n'
    '    <div class="success-sub" id="success-detail">Entry saved and on-hand updated automatically.</div>'
)
NEW_SUCCESS_HTML = (
    '    <div class="success-icon">✓</div>\n'
    '    <div class="success-title">Loss logged</div>\n'
    '    <div class="success-sub" id="success-detail">Entry saved and on-hand updated automatically.</div>\n'
    '    <div class="success-sub" id="success-thanks" style="margin-top:6px;font-weight:500;color:var(--navy);"></div>'
)

if OLD_SUCCESS_HTML in gl:
    gl = gl.replace(OLD_SUCCESS_HTML, NEW_SUCCESS_HTML, 1)
    print('OK: goods lost — added success-thanks div')
else:
    print('ERROR: goods lost success HTML not found')

# Populate the thank-you message in submitLoss JS
OLD_SUCCESS_JS = (
    "    document.getElementById('success-detail').textContent =\n"
    "      state.productName + ' · ' + state.category + ' · $' + valueLost.toFixed(2) + ' logged.';"
)
NEW_SUCCESS_JS = (
    "    document.getElementById('success-detail').textContent =\n"
    "      state.productName + ' · ' + state.category + ' · $' + valueLost.toFixed(2) + ' logged.';\n"
    "    (function(){\n"
    "      try {\n"
    "        var _u = JSON.parse(localStorage.getItem('medsync_user') || '{}');\n"
    "        var _name = (_u.full_name || '').split(' ')[0] || _u.full_name || '';\n"
    "        document.getElementById('success-thanks').textContent = _name ? 'Thank you, ' + _name + '!' : '';\n"
    "      } catch(e) {}\n"
    "    })();"
)

if OLD_SUCCESS_JS in gl:
    gl = gl.replace(OLD_SUCCESS_JS, NEW_SUCCESS_JS, 1)
    print('OK: goods lost — added thank-you JS')
else:
    print('ERROR: goods lost success JS not found')

with open(GL, 'w', encoding='utf-8') as f:
    f.write(gl)

print('Done.')
