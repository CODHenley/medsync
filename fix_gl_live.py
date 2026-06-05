"""Fix analytics: sidebar GL panel uses live data; PI chart skips category-only notes."""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'
path = f'{BASE}/medsync_analytics_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Sidebar GL panel — replace hardcoded block with dynamic IDs ─────────
old_sidebar = '''          <div class="pcontent" id="p-gl" style="display:none;">
          <div><div class="pc-title">Goods lost deep dive</div><div class="pc-sub">May 2026 · all locations · 47 submissions</div></div>
          <div class="mrow"><span class="mk">Total loss</span><span class="mv cr">$2,847</span></div>
          <div class="mrow"><span class="mk">vs. prior month</span><span class="mv ca">↑ $340 (+14%)</span></div>
          <div class="mrow"><span class="mk">Diagnostic duplicate</span><span class="mv ca">$1,248 · 44%</span></div>
          <div class="mrow"><span class="mk">Expired product</span><span class="mv">$724 · 25%</span></div>
          <div class="mrow"><span class="mk">In-house use</span><span class="mv cr">$481 · 17%</span></div>
          <div class="mrow"><span class="mk">Medication waste</span><span class="mv">$294 · 10%</span></div>
          <div class="mrow"><span class="mk">Damaged / Spilled</span><span class="mv">$100 · 4%</span></div>'''

new_sidebar = '''          <div class="pcontent" id="p-gl" style="display:none;">
          <div><div class="pc-title">Goods lost deep dive</div><div class="pc-sub" id="gl-sub">Month to date · all locations</div></div>
          <div class="mrow"><span class="mk">Total loss</span><span class="mv cr" id="gl-total">…</span></div>
          <div id="gl-cat-rows"></div>'''

if old_sidebar in src:
    src = src.replace(old_sidebar, new_sidebar, 1)
    print('OK: sidebar GL panel dynamic')
else:
    print('ERROR: sidebar GL panel not found')

# ── 2. renderGLBars — also update sidebar ─────────────────────────────────
old_render = "  }).join('') || '<div style=\"color:var(--mist);font-size:11px;padding:8px 0;\">No goods lost entries for this period.</div>';\n}"

new_render = (
    "  }).join('') || '<div style=\"color:var(--mist);font-size:11px;padding:8px 0;\">No goods lost entries for this period.</div>';\n"
    "  var totalEl=document.getElementById('gl-total'); if(totalEl) totalEl.textContent=fmt$(total);\n"
    "  var catRows=document.getElementById('gl-cat-rows');\n"
    "  if(catRows) catRows.innerHTML=sorted.slice(0,6).map(function(e){\n"
    "    var pct=total>0?Math.round((e[1]/total)*100):0;\n"
    "    return '<div class=\"mrow\"><span class=\"mk\">'+e[0]+'</span><span class=\"mv\">'+fmt$(e[1])+' · '+pct+'%</span></div>';\n"
    "  }).join('');\n"
    "}"
)

if old_render in src:
    src = src.replace(old_render, new_render, 1)
    print('OK: renderGLBars updates sidebar')
else:
    print('ERROR: renderGLBars end not found')

# ── 3. Fix loadPI — skip entries where notes start with a category name ────
CATS_CONST = "var _CATS=['Diagnostic duplicate','Expired product','Damaged / Spilled','Medication waste','In-house use','Other','Inhalants / Anesthesia Drugs','Controlled Substances (DEA)'];\n    "

old_pi = "if(Array.isArray(gl))gl.forEach(function(x){var n=(x.notes||'').split(' · ')[0].trim()||'Unknown';lostQ[n]=(lostQ[n]||0)+(x.qty_lost||1);lostV[n]=(lostV[n]||0)+parseFloat(x.value_lost||0);});"

new_pi = (
    CATS_CONST +
    "if(Array.isArray(gl))gl.forEach(function(x){\n"
    "      var raw=(x.notes||'').split(' · ')[0].trim();\n"
    "      if(!raw||_CATS.indexOf(raw)>=0) return;\n"
    "      lostQ[raw]=(lostQ[raw]||0)+(x.qty_lost||1);\n"
    "      lostV[raw]=(lostV[raw]||0)+parseFloat(x.value_lost||0);\n"
    "    });"
)

if old_pi in src:
    src = src.replace(old_pi, new_pi, 1)
    print('OK: loadPI skips category-only notes')
else:
    print('WARNING: loadPI pattern not found — skipping')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print('Done.')
