"""
Add two new roles:
1. receiver   — boots straight to hospital receiver only
2. hospital_manager — read-only analytics/reporting, no order/goods screens

Changes:
- medsync_login.html: new badge styles + two demo account buttons
- index.html: boot() handles new roles, nav badge text updated
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# ── 1. Login page ─────────────────────────────────────────────────────────────

with open(f'{BASE}/medsync_login.html', 'r', encoding='utf-8') as f:
    login = f.read()

# Add badge styles for new roles
old_badge_css = '.db-mgr{background:var(--green-bg);color:var(--green);}'
new_badge_css = (
    '.db-mgr{background:var(--green-bg);color:var(--green);}\n'
    '.db-recv{background:#E6F1FB;color:#1A6FAD;}\n'
    '.db-hmgr{background:#EEE8F5;color:#5B3FA8;}'
)
if old_badge_css in login:
    login = login.replace(old_badge_css, new_badge_css, 1)
    print('OK: login badge styles added')
else:
    print('ERROR: badge CSS anchor not found')

# Add new demo buttons
old_demos = (
    '        <button class="demo-btn" onclick="demoLogin(\'alex.m@scout.vet\')">\n'
    '          <div><div class="demo-name">Alex M.</div><div class="demo-role">alex.m@scout.vet · West Loop</div></div>\n'
    '          <span class="demo-badge db-mgr">Manager</span>\n'
    '        </button>\n'
    '      </div>'
)
new_demos = (
    '        <button class="demo-btn" onclick="demoLogin(\'alex.m@scout.vet\')">\n'
    '          <div><div class="demo-name">Alex M.</div><div class="demo-role">alex.m@scout.vet · West Loop</div></div>\n'
    '          <span class="demo-badge db-mgr">Manager</span>\n'
    '        </button>\n'
    '        <button class="demo-btn" onclick="demoLogin(\'casey.r@scout.vet\')">\n'
    '          <div><div class="demo-name">Casey R.</div><div class="demo-role">casey.r@scout.vet · Hospital Receiver</div></div>\n'
    '          <span class="demo-badge db-recv">Receiver</span>\n'
    '        </button>\n'
    '        <button class="demo-btn" onclick="demoLogin(\'dr.kim@scout.vet\')">\n'
    '          <div><div class="demo-name">Dr. Kim</div><div class="demo-role">dr.kim@scout.vet · Hospital Manager</div></div>\n'
    '          <span class="demo-badge db-hmgr">H. Manager</span>\n'
    '        </button>\n'
    '      </div>'
)
if old_demos in login:
    login = login.replace(old_demos, new_demos, 1)
    print('OK: new demo buttons added')
else:
    print('ERROR: demo buttons anchor not found')

with open(f'{BASE}/medsync_login.html', 'w', encoding='utf-8') as f:
    f.write(login)

# ── 2. index.html boot() ─────────────────────────────────────────────────────

with open(f'{BASE}/index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

# Update role badge text to handle new roles
old_badge = "if (rb) rb.textContent = user.role === 'admin' ? 'Admin' : 'Manager';"
new_badge = (
    "if (rb) rb.textContent = user.role === 'admin' ? 'Admin' :\n"
    "    user.role === 'hospital_manager' ? 'H. Manager' :\n"
    "    user.role === 'receiver' ? 'Receiver' : 'Manager';"
)
if old_badge in idx:
    idx = idx.replace(old_badge, new_badge, 1)
    print('OK: role badge text updated')
else:
    print('ERROR: role badge text not found')

# Update boot() to handle new roles
old_boot = (
    "  if (user.role === 'manager') {\n"
    "    ['mnb-portfolio','mnb-analytics','mnb-lifecycle','mnb-actlog'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    ['asb-portfolio','asb-analytics','asb-lifecycle','asb-actlog','asb-admin-label'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('order');\n"
    "  } else {\n"
    "    showScreen('portfolio');\n"
    "  }"
)
new_boot = (
    "  if (user.role === 'manager') {\n"
    "    ['mnb-portfolio','mnb-analytics','mnb-lifecycle','mnb-actlog'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    ['asb-portfolio','asb-analytics','asb-lifecycle','asb-actlog','asb-admin-label'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('order');\n"
    "  } else if (user.role === 'receiver') {\n"
    "    // Receiver: only hospital receiver screen\n"
    "    ['mnb-portfolio','mnb-analytics','mnb-lifecycle','mnb-actlog'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    ['asb-portfolio','asb-analytics','asb-lifecycle','asb-actlog',\n"
    "     'asb-order','asb-receiving','asb-goods','asb-admin-label'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('receiver');\n"
    "  } else if (user.role === 'hospital_manager') {\n"
    "    // Hospital manager: analytics/reporting only, read-only\n"
    "    ['asb-order','asb-receiving','asb-goods','asb-receiver'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('portfolio');\n"
    "  } else {\n"
    "    showScreen('portfolio');\n"
    "  }"
)
if old_boot in idx:
    idx = idx.replace(old_boot, new_boot, 1)
    print('OK: boot() updated with new roles')
else:
    print('ERROR: boot() block not found')

with open(f'{BASE}/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

print('\nDone. Next: create Supabase users (see SQL below).')
print("""
-- Run in Supabase SQL editor AFTER creating auth users for:
--   casey.r@scout.vet   (password: MedSync2026!)
--   dr.kim@scout.vet    (password: MedSync2026!)

-- Then insert into users table:
INSERT INTO users (id, full_name, role)
VALUES
  ((SELECT id FROM auth.users WHERE email='casey.r@scout.vet'),  'Casey R.', 'receiver'),
  ((SELECT id FROM auth.users WHERE email='dr.kim@scout.vet'),   'Dr. Kim',  'hospital_manager');
""")
