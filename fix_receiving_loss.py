"""
Two changes:
1. Remove Hospital Receiver from admin hamburger menu (asb-receiver)
2. Add inline ⚠ Loss button + Expired/Damaged/note to medsync_receiving_live.html
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# ── 1. Remove Hospital Receiver from hamburger menu ───────────────────────────
with open(f'{BASE}/index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

old_recv_menu = '  <div class="asb-item" id="asb-receiver" onclick="closeMobileMenu();showScreen(\'receiver\')">🏥 Hospital Receiver</div>\n'
if old_recv_menu in idx:
    idx = idx.replace(old_recv_menu, '', 1)
    print('OK: Hospital Receiver removed from hamburger menu')
else:
    print('ERROR: asb-receiver menu item not found')

with open(f'{BASE}/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

# ── 2. Add inline loss buttons to receiving screen ────────────────────────────
with open(f'{BASE}/medsync_receiving_live.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Add CSS for loss button and inline options (after existing badge CSS)
old_css = '.po-footer{background:var(--surface);border:0.5px solid var(--border);border-radius:10px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;}'
new_css = (
    '.po-footer{background:var(--surface);border:0.5px solid var(--border);border-radius:10px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;}\n'
    '.loss-btn{background:none;border:0.5px solid #C8922A;color:#C8922A;padding:3px 7px;border-radius:6px;font-size:10px;font-weight:600;cursor:pointer;font-family:\'DM Sans\',sans-serif;margin-left:6px;white-space:nowrap;}\n'
    '.loss-expand{padding:10px 16px 12px;background:#FEF8F0;border-top:0.5px solid #F0DDB0;display:flex;flex-direction:column;gap:8px;}\n'
    '.loss-note{font-size:13px;padding:8px 10px;border:0.5px solid var(--border);border-radius:8px;width:100%;box-sizing:border-box;font-family:\'DM Sans\',sans-serif;}\n'
    '.loss-btns{display:flex;gap:6px;}\n'
    '.loss-opt{flex:1;padding:7px 4px;border-radius:8px;border:0.5px solid;font-size:12px;font-weight:500;cursor:pointer;font-family:\'DM Sans\',sans-serif;}\n'
    '.loss-opt-exp{background:#FEF0F0;border-color:#E0AAAA;color:#C0392B;}\n'
    '.loss-opt-dmg{background:#FEF3E2;border-color:#E0C080;color:#A06020;}\n'
    '.loss-opt-cancel{background:#F5F3FA;border-color:var(--border);color:var(--mist);}\n'
    '.item-row.lost{background:#FEF8F0;}'
)
if old_css in src:
    src = src.replace(old_css, new_css, 1)
    print('OK: loss CSS added to receiving screen')
else:
    print('ERROR: po-footer CSS anchor not found')

# Add activeGoodsLine to state
old_state = 'const state = {'
new_state_check = 'activeGoodsLine: null,'
if new_state_check not in src:
    # Find the state object and add the property
    old_state_block = "  lastScanMsg: null,\n};"
    new_state_block = "  lastScanMsg: null,\n  activeGoodsLine: null,\n};"
    if old_state_block in src:
        src = src.replace(old_state_block, new_state_block, 1)
        print('OK: activeGoodsLine added to state')
    else:
        # Try alternate pattern
        import re
        src = re.sub(r'(const state = \{[^}]*?\n)\};', r'\1  activeGoodsLine: null,\n};', src, count=1, flags=re.DOTALL)
        print('OK: activeGoodsLine added via regex')

# Update renderItems to add loss button + expandable section
old_render = (
    "    return `<div class=\"item-row ${l.status}\" id=\"item-row-${i}\">\n"
    "      <div><div class=\"item-name\">${l.name}</div><div class=\"item-ndc\">${l.ndc}</div></div>\n"
    "      <div style=\"font-size:12px;\">${l.qtyOrdered}</div>\n"
    "      <div style=\"font-size:12px;font-weight:${l.qtyReceived?'500':'400'};color:${l.qtyReceived?'var(--navy)':'var(--mist)'};\">$"
    "{l.qtyReceived || '—'}</div>\n"
    "      <div style=\"font-size:11px;font-family:'DM Mono',monospace;color:var(--mist);\">${l.lotNum ? '#'+l.lotNum+'<br>Exp '+l.expDate : '—'}</div>\n"
    "      <div>${statusBadge}</div>\n"
    "    </div>`;"
)
new_render = (
    "    const lossExpanded = state.activeGoodsLine === i;\n"
    "    return `<div style=\"border-bottom:0.5px solid #F5F3FA;\">\n"
    "      <div class=\"item-row ${l.status === 'lost' ? 'lost' : l.status}\" id=\"item-row-${i}\" style=\"border-bottom:none;\">\n"
    "        <div><div class=\"item-name\" style=\"${l.status==='lost'?'text-decoration:line-through;color:var(--mist);':''}\">${l.name}</div><div class=\"item-ndc\">${l.ndc}</div></div>\n"
    "        <div style=\"font-size:12px;\">${l.qtyOrdered}</div>\n"
    "        <div style=\"font-size:12px;font-weight:${l.qtyReceived?'500':'400'};color:${l.qtyReceived?'var(--navy)':'var(--mist)'};\">$"
    "{l.qtyReceived || '—'}</div>\n"
    "        <div style=\"font-size:11px;font-family:'DM Mono',monospace;color:var(--mist);\">${l.lotNum ? '#'+l.lotNum+'<br>Exp '+l.expDate : '—'}</div>\n"
    "        <div style=\"display:flex;align-items:center;\">\n"
    "          ${l.status !== 'lost' ? statusBadge : '<span class=\"badge\" style=\"background:#FEF3E2;color:#A06020;border-color:#E0C080;\">⚠ Lost</span>'}\n"
    "          ${l.status !== 'lost' ? `<button class=\"loss-btn\" onclick=\"showReceivingLoss(${i})\">⚠ Loss</button>` : ''}\n"
    "        </div>\n"
    "      </div>\n"
    "      ${lossExpanded ? `\n"
    "        <div class=\"loss-expand\">\n"
    "          <input id=\"rloss-note-${i}\" class=\"loss-note\" type=\"text\" placeholder=\"Optional note (lot #, condition)…\">\n"
    "          <div class=\"loss-btns\">\n"
    "            <button class=\"loss-opt loss-opt-exp\" onclick=\"logReceivingLoss(${i},'Expired product')\">⏰ Expired</button>\n"
    "            <button class=\"loss-opt loss-opt-dmg\" onclick=\"logReceivingLoss(${i},'Damaged / Spilled')\">💧 Damaged</button>\n"
    "            <button class=\"loss-opt loss-opt-cancel\" onclick=\"state.activeGoodsLine=null;renderItems()\">Cancel</button>\n"
    "          </div>\n"
    "        </div>\n"
    "      ` : ''}\n"
    "    </div>`;"
)
if old_render in src:
    src = src.replace(old_render, new_render, 1)
    print('OK: renderItems updated with inline loss buttons')
else:
    print('ERROR: renderItems return block not found')

# Add showReceivingLoss + logReceivingLoss functions before updateStatus
old_anchor = 'function updateStatus() {'
new_fns = (
    'function showReceivingLoss(idx) {\n'
    '  state.activeGoodsLine = state.activeGoodsLine === idx ? null : idx;\n'
    '  renderItems();\n'
    '}\n'
    '\n'
    'async function logReceivingLoss(idx, category) {\n'
    '  const line = state.lines[idx];\n'
    '  const noteEl = document.getElementById(\'rloss-note-\' + idx);\n'
    '  const note = noteEl ? noteEl.value.trim() : \'\';\n'
    '  state.lines[idx].status = \'lost\';\n'
    '  state.activeGoodsLine = null;\n'
    '  renderItems();\n'
    '  updateStatus();\n'
    '  showToast(\'⚠ \' + line.name + \' logged as \' + category);\n'
    '  const _sess = (function(){ try { return JSON.parse(localStorage.getItem(\'medsync_session\') || \'{}\')); } catch(e) { return {}; } })();\n'
    '  const _H = { \'apikey\': SUPA_KEY, \'Authorization\': \'Bearer \' + (_sess.access_token || SUPA_KEY), \'Content-Type\': \'application/json\', \'Prefer\': \'return=minimal\' };\n'
    '  fetch(SUPA_URL + \'/rest/v1/goods_lost\', {\n'
    '    method: \'POST\', headers: _H,\n'
    '    body: JSON.stringify({\n'
    '      location_id: state.locationId,\n'
    '      category:    category,\n'
    '      qty_lost:    1,\n'
    '      value_lost:  0,\n'
    '      notes:       line.name + (note ? \' · \' + note : \'\') + \' · Logged via PO Receiving\',\n'
    '    })\n'
    '  }).catch(() => {});\n'
    '}\n'
    '\n'
    'function updateStatus() {'
)
if 'function updateStatus() {' in src:
    src = src.replace('function updateStatus() {', new_fns, 1)
    print('OK: showReceivingLoss + logReceivingLoss added')
else:
    print('ERROR: updateStatus anchor not found')

with open(f'{BASE}/medsync_receiving_live.html', 'w', encoding='utf-8') as f:
    f.write(src)

print('Done.')
