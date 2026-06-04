"""
Add "Purchase Intelligence" section to analytics:
1. Purchase vs. Goods Lost by product (dual horizontal bars)
2. Top waste contributors (value lost by product)
3. Lot expiry risk (lots expiring in 30/60/90 days by product)
All charts pull live from Supabase with demo fallback.
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

with open(f'{BASE}/medsync_analytics_live.html', 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Add CSS for purchase intelligence charts ───────────────────────────────
old_css_anchor = '.oc-bar{width:48px;height:4px;background:#E4E0F0;border-radius:2px;overflow:hidden;}'
new_css = (
    '.oc-bar{width:48px;height:4px;background:#E4E0F0;border-radius:2px;overflow:hidden;}\n'
    '/* Purchase Intelligence */\n'
    '.pi-section-title{font-size:11px;font-weight:700;color:var(--navy);text-transform:uppercase;letter-spacing:.06em;margin:4px 0 12px;padding-bottom:8px;border-bottom:0.5px solid var(--border);}\n'
    '.pi-row{display:flex;flex-direction:column;gap:4px;margin-bottom:12px;}\n'
    '.pi-label{font-size:11px;font-weight:500;color:var(--navy);display:flex;justify-content:space-between;}\n'
    '.pi-label-sub{font-size:10px;color:var(--mist);font-weight:400;}\n'
    '.pi-bars{display:flex;flex-direction:column;gap:3px;}\n'
    '.pi-bar-row{display:flex;align-items:center;gap:6px;}\n'
    '.pi-bar-label{font-size:10px;color:var(--mist);width:44px;text-align:right;flex-shrink:0;}\n'
    '.pi-track{flex:1;height:10px;background:#F0EEF8;border-radius:3px;overflow:hidden;}\n'
    '.pi-fill-buy{height:100%;background:#1C6FAD;border-radius:3px;}\n'
    '.pi-fill-lost{height:100%;background:#C8922A;border-radius:3px;}\n'
    '.pi-fill-exp{height:100%;background:#C0392B;border-radius:3px;}\n'
    '.pi-val{font-size:10px;width:36px;text-align:right;flex-shrink:0;font-weight:500;}\n'
    '.pi-legend{display:flex;gap:12px;margin-bottom:10px;}\n'
    '.pi-leg-item{display:flex;align-items:center;gap:4px;font-size:10px;color:var(--mist);}\n'
    '.pi-leg-dot{width:8px;height:8px;border-radius:2px;flex-shrink:0;}'
)
if old_css_anchor in src:
    src = src.replace(old_css_anchor, new_css, 1)
    print('OK: Purchase Intelligence CSS added')
else:
    print('ERROR: CSS anchor not found')

# ── 2. Add HTML cards before </div><!-- /main-col --> ────────────────────────
old_end = '      </div><!-- /main-col -->'
new_cards = '''
        <!-- ══ PURCHASE INTELLIGENCE ══════════════════════════════ -->
        <div class="card">
          <div class="card-head">
            <div class="card-title" id="pi-title">Purchase Intelligence — Month to date</div>
            <div class="card-sub">Ordered vs. goods lost · all locations</div>
          </div>
          <div style="padding:16px;">
            <div class="pi-section-title">Purchase volume vs. goods lost by product</div>
            <div class="pi-legend">
              <div class="pi-leg-item"><div class="pi-leg-dot" style="background:#1C6FAD;"></div>Purchased (units)</div>
              <div class="pi-leg-item"><div class="pi-leg-dot" style="background:#C8922A;"></div>Lost (units)</div>
            </div>
            <div id="pi-pvl-rows">
              <div style="color:var(--mist);font-size:12px;">Loading…</div>
            </div>
          </div>
        </div>

        <!-- Waste rate by product -->
        <div class="card">
          <div class="card-head">
            <div class="card-title" id="pi-waste-title">Top waste contributors — Month to date</div>
            <div class="card-sub">Goods lost value by product · all locations</div>
          </div>
          <div style="padding:16px;">
            <div id="pi-waste-rows">
              <div style="color:var(--mist);font-size:12px;">Loading…</div>
            </div>
          </div>
        </div>

        <!-- Lot expiry risk -->
        <div class="card">
          <div class="card-head">
            <div class="card-title">Lot expiry risk — next 90 days</div>
            <div class="card-sub">Lots expiring by product · action required</div>
          </div>
          <div style="padding:16px;">
            <div class="pi-legend">
              <div class="pi-leg-item"><div class="pi-leg-dot" style="background:#C0392B;"></div>Expired / &lt;30d</div>
              <div class="pi-leg-item"><div class="pi-leg-dot" style="background:#C8922A;"></div>30–60d</div>
              <div class="pi-leg-item"><div class="pi-leg-dot" style="background:#1C6FAD;"></div>60–90d</div>
            </div>
            <div id="pi-expiry-rows">
              <div style="color:var(--mist);font-size:12px;">Loading…</div>
            </div>
          </div>
        </div>

      </div><!-- /main-col -->'''

if old_end in src:
    src = src.replace(old_end, new_cards, 1)
    print('OK: Purchase Intelligence cards added')
else:
    print('ERROR: main-col end not found')

# ── 3. Add JavaScript to load the purchase intelligence data ─────────────────
old_js_anchor = '// Hide nav and internal sidebar when running inside an iframe'
new_js = '''// ── Purchase Intelligence data loaders ────────────────────────────────────
async function loadPurchaseIntelligence() {
  try {
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

    // Fetch order lines (purchases this month)
    const olRes = await fetch(
      SUPA_URL + '/rest/v1/order_lines?select=qty_ordered,products(id,name)&order=qty_ordered.desc',
      { headers: H }
    );
    const olData = await olRes.json();

    // Aggregate purchases by product
    const purchased = {};
    if (Array.isArray(olData)) {
      olData.forEach(function(ol) {
        const name = ol.products && ol.products.name ? ol.products.name : null;
        if (!name) return;
        purchased[name] = (purchased[name] || 0) + (ol.qty_ordered || 0);
      });
    }

    // Fetch goods lost this month
    const glRes = await fetch(
      SUPA_URL + '/rest/v1/goods_lost?select=qty_lost,value_lost,notes,category&created_at=gte.' + monthStart,
      { headers: H }
    );
    const glData = await glRes.json();

    // Aggregate lost by product (extracted from notes)
    const lostQty = {}, lostVal = {};
    if (Array.isArray(glData)) {
      glData.forEach(function(gl) {
        // Product name is first segment of notes before ' · '
        var raw = (gl.notes || '').split(' · ')[0].trim();
        var name = raw || gl.category || 'Unknown';
        lostQty[name] = (lostQty[name] || 0) + (gl.qty_lost || 1);
        lostVal[name]  = (lostVal[name]  || 0) + parseFloat(gl.value_lost || 0);
      });
    }

    // Merge keys
    var allProducts = Array.from(new Set([...Object.keys(purchased), ...Object.keys(lostQty)]));

    // If no real data, use demo fallback
    if (allProducts.length === 0) {
      allProducts = ['Buprenorphine 0.3mg/ml','Ketamine HCl 10mg/ml','Gabapentin 100mg caps',
        'Carprofen 50mg tabs','Dexmedetomidine 0.5mg/ml','Maropitant Citrate 10mg/ml'];
      allProducts.forEach(function(p, i) {
        purchased[p] = [20,15,214,180,10,8][i];
        lostQty[p]   = [2,1,14,5,1,0][i];
        lostVal[p]   = [376,142,10,12,110,0][i];
      });
    }

    // Sort by purchased desc, top 8
    allProducts.sort(function(a,b){ return (purchased[b]||0) - (purchased[a]||0); });
    allProducts = allProducts.slice(0, 8);

    var maxBuy  = Math.max.apply(null, allProducts.map(function(p){ return purchased[p]||0; })) || 1;
    var maxLost = Math.max.apply(null, allProducts.map(function(p){ return lostQty[p]||0; })) || 1;
    var maxBar  = Math.max(maxBuy, maxLost);

    // Render purchase vs lost
    var pvlHtml = allProducts.map(function(name) {
      var buy  = purchased[name] || 0;
      var lost = lostQty[name]   || 0;
      var lossRate = buy > 0 ? Math.round((lost/buy)*100) : 0;
      var shortName = name.length > 22 ? name.substring(0,20) + '…' : name;
      return '<div class="pi-row">' +
        '<div class="pi-label"><span>' + shortName + '</span>' +
        (lossRate > 0 ? '<span class="pi-label-sub" style="color:' + (lossRate>10?'var(--red)':'var(--amber)') + ';">' + lossRate + '% loss rate</span>' : '<span class="pi-label-sub" style="color:var(--green);">0% loss</span>') +
        '</div>' +
        '<div class="pi-bars">' +
          '<div class="pi-bar-row"><span class="pi-bar-label">Ordered</span>' +
            '<div class="pi-track"><div class="pi-fill-buy" style="width:' + Math.round((buy/maxBar)*100) + '%;"></div></div>' +
            '<span class="pi-val" style="color:#1C6FAD;">' + buy + '</span></div>' +
          '<div class="pi-bar-row"><span class="pi-bar-label">Lost</span>' +
            '<div class="pi-track"><div class="pi-fill-lost" style="width:' + Math.round((lost/maxBar)*100) + '%;"></div></div>' +
            '<span class="pi-val" style="color:' + (lost>0?'var(--amber)':'var(--mist)') + ';">' + lost + '</span></div>' +
        '</div></div>';
    }).join('');
    document.getElementById('pi-pvl-rows').innerHTML = pvlHtml || '<div style="color:var(--mist);font-size:12px;">No data yet.</div>';

    // Render waste by value (top 8, sorted by value)
    var wasteProducts = Object.keys(lostVal).filter(function(p){ return lostVal[p] > 0; });
    wasteProducts.sort(function(a,b){ return lostVal[b] - lostVal[a]; });
    wasteProducts = wasteProducts.slice(0, 8);
    var maxWaste = wasteProducts.length > 0 ? lostVal[wasteProducts[0]] : 1;

    var wasteHtml = wasteProducts.map(function(name) {
      var val = lostVal[name] || 0;
      var shortName = name.length > 26 ? name.substring(0,24) + '…' : name;
      return '<div class="pi-row" style="margin-bottom:8px;">' +
        '<div class="pi-label"><span>' + shortName + '</span>' +
        '<span class="pi-label-sub" style="color:var(--red);">$' + val.toFixed(2) + '</span></div>' +
        '<div class="pi-bar-row">' +
          '<div class="pi-track" style="height:12px;"><div class="pi-fill-lost" style="width:' + Math.round((val/maxWaste)*100) + '%;height:100%;"></div></div>' +
        '</div></div>';
    }).join('');
    document.getElementById('pi-waste-rows').innerHTML = wasteHtml ||
      '<div style="color:var(--mist);font-size:12px;text-align:center;padding:8px;">No goods lost recorded this month.</div>';

  } catch(e) {
    console.error('loadPurchaseIntelligence:', e);
  }
}

async function loadExpiryRisk() {
  try {
    const now = new Date();
    const d30  = new Date(now.getTime() + 30*24*60*60*1000).toISOString().split('T')[0];
    const d60  = new Date(now.getTime() + 60*24*60*60*1000).toISOString().split('T')[0];
    const d90  = new Date(now.getTime() + 90*24*60*60*1000).toISOString().split('T')[0];
    const today = now.toISOString().split('T')[0];

    const lotRes = await fetch(
      SUPA_URL + '/rest/v1/lots?select=expiration_date,qty_remaining,products(name)&expiration_date=lte.' + d90 + '&disposal_date=is.null&order=expiration_date.asc',
      { headers: H }
    );
    const lots = await lotRes.json();

    // Aggregate by product + bucket
    var byProduct = {};
    if (Array.isArray(lots) && lots.length > 0) {
      lots.forEach(function(lot) {
        var name = lot.products && lot.products.name ? lot.products.name : 'Unknown';
        if (!byProduct[name]) byProduct[name] = { expired:0, d30:0, d60:0 };
        var exp = lot.expiration_date;
        var qty = lot.qty_remaining || 1;
        if (exp <= today) byProduct[name].expired += qty;
        else if (exp <= d30) byProduct[name].d30 += qty;
        else if (exp <= d60) byProduct[name].d60 += qty;
        else byProduct[name].d60 += qty; // 60-90d bucket
      });
    }

    // Demo fallback
    if (Object.keys(byProduct).length === 0) {
      byProduct = {
        'Ketamine HCl 10mg/ml':     { expired:1, d30:0, d60:1 },
        'Dexmedetomidine 0.5mg/ml': { expired:1, d30:0, d60:0 },
        'Buprenorphine 0.3mg/ml':   { expired:0, d30:2, d60:1 },
        'Carprofen 50mg tabs':      { expired:0, d30:1, d60:2 },
        'Gabapentin 100mg caps':    { expired:0, d30:0, d60:3 },
      };
    }

    var prods = Object.keys(byProduct);
    var maxExp = Math.max.apply(null, prods.map(function(p){
      var b = byProduct[p]; return b.expired + b.d30 + b.d60;
    })) || 1;

    var expHtml = prods.map(function(name) {
      var b = byProduct[name];
      var total = b.expired + b.d30 + b.d60;
      var shortName = name.length > 26 ? name.substring(0,24) + '…' : name;
      var pExp = Math.round((b.expired/maxExp)*100);
      var p30  = Math.round((b.d30/maxExp)*100);
      var p60  = Math.round((b.d60/maxExp)*100);
      return '<div class="pi-row" style="margin-bottom:10px;">' +
        '<div class="pi-label"><span>' + shortName + '</span>' +
        '<span class="pi-label-sub" style="color:' + (b.expired>0?'var(--red)':b.d30>0?'var(--amber)':'var(--navy)') + ';">' +
        total + ' lot' + (total!==1?'s':'') + (b.expired>0?' · '+b.expired+' expired':'') + '</span></div>' +
        '<div class="pi-bar-row">' +
          '<div class="pi-track" style="height:12px;display:flex;background:#F0EEF8;overflow:hidden;border-radius:3px;">' +
            (pExp>0?'<div style="width:'+pExp+'%;background:#C0392B;height:100%;"></div>':'') +
            (p30>0?'<div style="width:'+p30+'%;background:#C8922A;height:100%;"></div>':'') +
            (p60>0?'<div style="width:'+p60+'%;background:#1C6FAD;height:100%;"></div>':'') +
          '</div>' +
        '</div></div>';
    }).join('');
    document.getElementById('pi-expiry-rows').innerHTML = expHtml ||
      '<div style="color:var(--green);font-size:12px;text-align:center;padding:8px;">✓ No lots expiring in the next 90 days.</div>';

  } catch(e) {
    console.error('loadExpiryRisk:', e);
  }
}

// Hook into existing loadData function
'''

if old_js_anchor in src:
    src = src.replace(old_js_anchor, new_js + old_js_anchor, 1)
    print('OK: Purchase Intelligence JS added')
else:
    print('ERROR: JS anchor not found')

# ── 4. Call the new loaders from the existing loadData function ───────────────
old_load_end = 'async function loadData() {'
# Find where loadData ends by looking for what it calls
load_trigger = '  if (typeof renderLocationFilter === '
# Actually just add calls after the existing load calls
old_doc_ready = "document.addEventListener('DOMContentLoaded', function() {"
if old_doc_ready in src:
    src = src.replace(
        old_doc_ready,
        "document.addEventListener('DOMContentLoaded', function() {\n  loadPurchaseIntelligence();\n  loadExpiryRisk();",
        1
    )
    print('OK: loaders called on DOMContentLoaded')
else:
    # Try window load
    old_win = "window.addEventListener('load',"
    if old_win in src:
        print('WARNING: using window.load fallback')
    else:
        # Call directly at bottom of script
        old_boot_call = 'if (window.self !== window.top)'
        if old_boot_call in src:
            src = src.replace(old_boot_call,
                'loadPurchaseIntelligence();\nloadExpiryRisk();\n' + old_boot_call, 1)
            print('OK: loaders called before iframe check')
        else:
            print('WARNING: could not find call site — loaders added but not called')

with open(f'{BASE}/medsync_analytics_live.html', 'w', encoding='utf-8') as f:
    f.write(src)

print('Done.')
