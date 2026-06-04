"""
Redesign hospital receiver flow:
1. Welcome → loads orders directly (skip task screen)
2. Scan view: each item has an inline ⚠ Loss button
3. Tapping Loss shows Expired / Damaged inline — no separate screen
4. Remove standalone goods lost screen/task
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'
path = f'{BASE}/medsync_hospital_receiver_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Add activeGoodsLine to state ──────────────────────────────────────────
old_state = (
    "  goodsProductName: '',\n"
    "  goodsProductId: null,\n"
    "};"
)
new_state = (
    "  goodsProductName: '',\n"
    "  goodsProductId: null,\n"
    "  activeGoodsLine: null,\n"
    "};"
)
if old_state in src:
    src = src.replace(old_state, new_state, 1)
    print("OK: state.activeGoodsLine added")
else:
    print("ERROR: state block not found")

# ── 2. onNameNext → skip task, load orders directly ──────────────────────────
old_next = (
    "  state.name = name;\n"
    "  state.locationId = locSel.value;\n"
    "  state.locationName = locSel.options[locSel.selectedIndex].text;\n"
    "  state.screen = 'task';\n"
    "  render();"
)
new_next = (
    "  state.name = name;\n"
    "  state.locationId = locSel.value;\n"
    "  state.locationName = locSel.options[locSel.selectedIndex].text;\n"
    "  onTaskSelect('receive');"
)
if old_next in src:
    src = src.replace(old_next, new_next, 1)
    print("OK: onNameNext skips task screen")
else:
    print("ERROR: onNameNext block not found")

# ── 3. Replace scan items to include per-item loss button ────────────────────
old_items = (
    "        <div class=\"scan-items\">\n"
    "          ${state.lines.map(l => `\n"
    "            <div class=\"scan-item ${l.status}\">\n"
    "              <span class=\"si-name\">${l.name}</span>\n"
    "              <span class=\"si-badge ${l.status==='confirmed'?'b-ok':'b-pend'}\">${l.status==='confirmed'?'✓ Done':'Awaiting'}</span>\n"
    "            </div>`).join('')}\n"
    "        </div>"
)
new_items = (
    "        <div class=\"scan-items\">\n"
    "          ${state.lines.map((l,i) => `\n"
    "            <div class=\"scan-item ${l.status}\" style=\"flex-direction:column;align-items:stretch;gap:0;\">\n"
    "              <div style=\"display:flex;align-items:center;justify-content:space-between;\">\n"
    "                <span class=\"si-name\" style=\"${l.status==='lost'?'text-decoration:line-through;color:var(--mist);':''}\">${l.name}</span>\n"
    "                <div style=\"display:flex;align-items:center;gap:6px;\">\n"
    "                  ${l.status !== 'lost' ? `<button class=\"loss-btn\" onclick=\"event.stopPropagation();showLossOptions(${i})\">⚠ Loss</button>` : ''}\n"
    "                  <span class=\"si-badge ${l.status==='confirmed'?'b-ok':l.status==='lost'?'b-warn':'b-pend'}\">${l.status==='confirmed'?'✓ Done':l.status==='lost'?'⚠ Lost':'Awaiting'}</span>\n"
    "                </div>\n"
    "              </div>\n"
    "              ${state.activeGoodsLine === i ? `\n"
    "                <div class=\"loss-opts\">\n"
    "                  <button class=\"loss-opt loss-opt-exp\" onclick=\"hrLogGoodsLine(${i},'Expired product')\">⏰ Expired</button>\n"
    "                  <button class=\"loss-opt loss-opt-dmg\" onclick=\"hrLogGoodsLine(${i},'Damaged / Spilled')\">💧 Damaged</button>\n"
    "                  <button class=\"loss-opt loss-opt-cancel\" onclick=\"state.activeGoodsLine=null;render()\">Cancel</button>\n"
    "                </div>\n"
    "              ` : ''}\n"
    "            </div>`).join('')}\n"
    "        </div>"
)
if old_items in src:
    src = src.replace(old_items, new_items, 1)
    print("OK: scan items updated with inline loss buttons")
else:
    print("ERROR: scan items block not found")

# ── 4. Add showLossOptions + hrLogGoodsLine functions ────────────────────────
old_hrlog = "async function hrLogGoods(category) {"
new_fns = (
    "function showLossOptions(idx) {\n"
    "  state.activeGoodsLine = state.activeGoodsLine === idx ? null : idx;\n"
    "  render();\n"
    "}\n"
    "\n"
    "async function hrLogGoodsLine(idx, category) {\n"
    "  const line = state.lines[idx];\n"
    "  state.lines[idx].status = 'lost';\n"
    "  state.activeGoodsLine = null;\n"
    "  render();\n"
    "  showToast('⚠ ' + line.name + ' logged as ' + category);\n"
    "  fetch(SUPA_URL + '/rest/v1/goods_lost', {\n"
    "    method: 'POST',\n"
    "    headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "    body: JSON.stringify({\n"
    "      location_id: state.locationId,\n"
    "      category:    category,\n"
    "      qty_lost:    1,\n"
    "      value_lost:  0,\n"
    "      notes:       line.name + ' · Submitted by ' + state.name + ' via Hospital Receiver',\n"
    "    })\n"
    "  }).catch(() => {});\n"
    "  fetch(SUPA_URL + '/rest/v1/activity_log', {\n"
    "    method: 'POST',\n"
    "    headers: { ...H, 'Prefer': 'return=minimal' },\n"
    "    body: JSON.stringify({\n"
    "      location_id: state.locationId,\n"
    "      event_type:  'goods',\n"
    "      description: 'Goods lost: ' + line.name + ' (' + category + ')',\n"
    "      flag:        'ok',\n"
    "      metadata:    { category, product: line.name, submitted_by: state.name }\n"
    "    })\n"
    "  }).catch(() => {});\n"
    "}\n"
    "\n"
    "async function hrLogGoods(category) {"
)
if old_hrlog in src:
    src = src.replace(old_hrlog, new_fns, 1)
    print("OK: showLossOptions + hrLogGoodsLine added")
else:
    print("ERROR: hrLogGoods not found for insertion point")

# ── 5. Add CSS for loss button and inline options ─────────────────────────────
old_css_anchor = ".btn-secondary{width:100%;padding:13px;border:0.5px solid var(--border);background:#fff;color:var(--navy);border-radius:12px;font-size:14px;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;}"
new_css = (
    ".btn-secondary{width:100%;padding:13px;border:0.5px solid var(--border);background:#fff;color:var(--navy);border-radius:12px;font-size:14px;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;}\n"
    ".b-warn{background:#FEF3E2;color:#C07830;border-color:#E0C080;}\n"
    ".loss-btn{background:none;border:0.5px solid #C8922A;color:#C8922A;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;}\n"
    ".loss-opts{display:flex;gap:6px;padding:8px 0 2px;}\n"
    ".loss-opt{flex:1;padding:8px 4px;border-radius:8px;border:0.5px solid;font-size:12px;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;}\n"
    ".loss-opt-exp{background:#FEF0F0;border-color:#E0AAAA;color:#C0392B;}\n"
    ".loss-opt-dmg{background:#FEF3E2;border-color:#E0C080;color:#A06020;}\n"
    ".loss-opt-cancel{background:#F5F3FA;border-color:var(--border);color:var(--mist);}"
)
if old_css_anchor in src:
    src = src.replace(old_css_anchor, new_css, 1)
    print("OK: loss button CSS added")
else:
    print("ERROR: CSS anchor not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("Done.")
