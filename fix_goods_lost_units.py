import sys

path = '/sessions/peaceful-confident-bell/mnt/medsync_deploy/medsync_goods_lost_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Fetch dispensing_unit and package_size in loadProducts()
OLD_LOAD = "  const res = await fetch(SUPA_URL + '/rest/v1/products?select=id,name,category&order=name', { headers: H });\n  const prods = await res.json();\n  const sel = document.getElementById('product-select');\n  prods.forEach(p => {\n    const opt = document.createElement('option');\n    opt.value = p.id;\n    opt.textContent = p.name;\n    opt.dataset.price = getPriceEstimate(p.name);\n    sel.appendChild(opt);\n  });"

NEW_LOAD = (
    "  const res = await fetch(SUPA_URL + '/rest/v1/products?select=id,name,category,dispensing_unit,package_size&order=name', { headers: H });\n"
    "  const prods = await res.json();\n"
    "  const sel = document.getElementById('product-select');\n"
    "  prods.forEach(p => {\n"
    "    const opt = document.createElement('option');\n"
    "    opt.value = p.id;\n"
    "    opt.textContent = p.name;\n"
    "    opt.dataset.price = getPriceEstimate(p.name);\n"
    "    opt.dataset.unit = p.dispensing_unit || 'units';\n"
    "    opt.dataset.pkgSize = p.package_size || 1;\n"
    "    sel.appendChild(opt);\n"
    "  });"
)

# 2. Store unit and package_size in state on product change
OLD_PRODUCT_CHANGE = (
    "function onProductChange() {\n"
    "  const sel = document.getElementById('product-select');\n"
    "  const opt = sel.options[sel.selectedIndex];\n"
    "  state.productId = sel.value;\n"
    "  state.productName = opt.text;\n"
    "  state.productPrice = parseFloat(opt.dataset.price) || 0;\n"
    "  updateValueDisplay();\n"
    "}"
)

NEW_PRODUCT_CHANGE = (
    "function onProductChange() {\n"
    "  const sel = document.getElementById('product-select');\n"
    "  const opt = sel.options[sel.selectedIndex];\n"
    "  state.productId = sel.value;\n"
    "  state.productName = opt.text;\n"
    "  state.productPrice = parseFloat(opt.dataset.price) || 0;\n"
    "  state.productUnit = opt.dataset.unit || 'units';\n"
    "  state.productPkgSize = parseFloat(opt.dataset.pkgSize) || 1;\n"
    "  document.getElementById('qty-unit').textContent = state.productUnit;\n"
    "  updateValueDisplay();\n"
    "}"
)

# 3. Update value calculation to use per-dispensing-unit cost
OLD_VALUE = (
    "function updateValueDisplay() {\n"
    "  const val = (state.productPrice || 0) * state.qty;\n"
    "  document.getElementById('loss-value').textContent = val > 0 ? '$' + val.toFixed(2) + ' loss' : '—';\n"
    "}"
)

NEW_VALUE = (
    "function updateValueDisplay() {\n"
    "  const pkgSize = state.productPkgSize || 1;\n"
    "  const costPerUnit = (state.productPrice || 0) / pkgSize;\n"
    "  const val = costPerUnit * (state.qty || 1);\n"
    "  document.getElementById('loss-value').textContent = val > 0 ? '$' + val.toFixed(2) + ' loss' : '—';\n"
    "}"
)

# 4. Add productUnit and productPkgSize to state, update value_lost in submitLoss
OLD_STATE = (
    "let state = {\n"
    "  locationId: null,\n"
    "  locationName: null,\n"
    "  productId: null,\n"
    "  productName: null,\n"
    "  productPrice: null,\n"
    "  category: 'Diagnostic duplicate',\n"
    "  subCategory: 'Confirm results',\n"
    "  qty: 1,\n"
    "  note: ''\n"
    "};"
)

NEW_STATE = (
    "let state = {\n"
    "  locationId: null,\n"
    "  locationName: null,\n"
    "  productId: null,\n"
    "  productName: null,\n"
    "  productPrice: null,\n"
    "  productUnit: 'units',\n"
    "  productPkgSize: 1,\n"
    "  category: 'Diagnostic duplicate',\n"
    "  subCategory: 'Confirm results',\n"
    "  qty: 1,\n"
    "  note: ''\n"
    "};"
)

# 5. Fix qty reset to also reset unit label
OLD_RESET = "  state.qty = 1;"
NEW_RESET = (
    "  state.qty = 1;\n"
    "  state.productUnit = 'units';\n"
    "  state.productPkgSize = 1;\n"
    "  document.getElementById('qty-unit').textContent = 'units';"
)

errors = []
for old, new, desc in [
    (OLD_LOAD, NEW_LOAD, 'loadProducts fetch'),
    (OLD_PRODUCT_CHANGE, NEW_PRODUCT_CHANGE, 'onProductChange'),
    (OLD_VALUE, NEW_VALUE, 'updateValueDisplay'),
    (OLD_STATE, NEW_STATE, 'state declaration'),
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

# Apply reset fix (may appear multiple times — only patch the one inside submitLoss reset block)
# Find the reset block context
reset_target = "  state.qty = 1;\n  document.getElementById"
if reset_target in src:
    src = src.replace("  state.qty = 1;\n  document.getElementById", NEW_RESET + "\n  document.getElementById", 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("OK: medsync_goods_lost_live.html patched.")
print("Next: update the HTML qty label element, then deploy.")
