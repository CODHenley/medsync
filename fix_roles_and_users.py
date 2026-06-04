"""
1. Give admin and manager identical screen access
2. Add User Management screen (admin creates all roles; manager creates receiver/inventory_lead)
3. Add inventory_lead role to the system
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'

# ── 1. Update index.html ──────────────────────────────────────────────────────

with open(f'{BASE}/index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

# A. Add 'users' to __screens list
old_screens = "var __screens = ['portfolio','analytics','lifecycle','actlog','order','receiving','receiver','goods'];"
new_screens = "var __screens = ['portfolio','analytics','lifecycle','actlog','order','receiving','receiver','goods','users'];"
if old_screens in idx:
    idx = idx.replace(old_screens, new_screens, 1)
    print('OK: users screen added to __screens')
else:
    print('ERROR: __screens not found')

# B. Add Users nav item to hamburger menu (after goods lost)
old_nav = '  <div class="asb-item" id="asb-goods" onclick="closeMobileMenu();showScreen(\'goods\')">⚠️ Goods Lost</div>'
new_nav = (
    '  <div class="asb-item" id="asb-goods" onclick="closeMobileMenu();showScreen(\'goods\')">⚠️ Goods Lost</div>\n'
    '  <div class="asb-item" id="asb-users" onclick="closeMobileMenu();showScreen(\'users\')">👥 Manage Users</div>'
)
if old_nav in idx:
    idx = idx.replace(old_nav, new_nav, 1)
    print('OK: Manage Users added to hamburger menu')
else:
    print('ERROR: goods nav item not found')

# C. Add users screen div (after ms-goods)
old_goods_div = '<div id="ms-goods" class="ms-screen">\n  <iframe src="medsync_goods_lost_live.html"'
new_goods_div = (
    '<div id="ms-goods" class="ms-screen">\n  <iframe src="medsync_goods_lost_live.html"'
)
# Add after the closing tag of ms-goods iframe
old_after = '<div id="ms-toast"></div>'
new_after = (
    '<div id="ms-users" class="ms-screen">\n'
    '  <iframe src="medsync_users_live.html"\n'
    '    style="width:100%;height:calc(100vh - 48px);border:none;display:block;"\n'
    '    title="User Management">\n'
    '  </iframe>\n'
    '</div>\n'
    '<div id="ms-toast"></div>'
)
if old_after in idx:
    idx = idx.replace(old_after, new_after, 1)
    print('OK: ms-users screen div added')
else:
    print('ERROR: ms-toast anchor not found')

# D. Update boot() - manager gets same access as admin; add users screen to receiver/hospital_manager hide list
old_boot = (
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
new_boot = (
    "  // manager and admin have identical access\n"
    "  if (user.role === 'receiver') {\n"
    "    // Receiver: only hospital receiver screen\n"
    "    ['mnb-portfolio','mnb-analytics','mnb-lifecycle','mnb-actlog'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    ['asb-portfolio','asb-analytics','asb-lifecycle','asb-actlog',\n"
    "     'asb-order','asb-receiving','asb-goods','asb-users','asb-admin-label'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('receiver');\n"
    "  } else if (user.role === 'hospital_manager') {\n"
    "    // Hospital manager: analytics/reporting only, read-only\n"
    "    ['asb-order','asb-receiving','asb-goods','asb-receiver','asb-users'].forEach(function(id){\n"
    "      var el = document.getElementById(id); if (el) el.style.display = 'none';\n"
    "    });\n"
    "    showScreen('portfolio');\n"
    "  } else {\n"
    "    // admin + manager: full access\n"
    "    showScreen('portfolio');\n"
    "  }"
)
if old_boot in idx:
    idx = idx.replace(old_boot, new_boot, 1)
    print('OK: boot() updated — manager = admin access')
else:
    print('ERROR: boot() block not found')

# E. Add ms-users to mobile padding group
old_mobile_pad = "  #ms-portfolio, #ms-order, #ms-receiving, #ms-goods {"
new_mobile_pad = "  #ms-portfolio, #ms-order, #ms-receiving, #ms-goods, #ms-users {"
if old_mobile_pad in idx:
    idx = idx.replace(old_mobile_pad, new_mobile_pad, 1)
    print('OK: ms-users added to mobile padding group')
else:
    print('WARNING: mobile padding group not found — skipping')

with open(f'{BASE}/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

# ── 2. Create medsync_users_live.html ─────────────────────────────────────────

users_html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MedSync · User Management</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--navy:#1C2B4A;--green:#2E8B57;--green-bg:#E8F5EE;--amber:#C8922A;--amber-bg:#FEF3E2;--red:#C0392B;--red-bg:#FDECEA;--mist:#8A93A8;--border:#DDD9EC;--surface:#FFFFFF;--purple:#5B3FA8;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:#F5F3FA;color:var(--navy);font-size:13px;}
.topbar{background:var(--navy);padding:0 24px;height:48px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.tb-title{font-size:15px;font-weight:600;color:#fff;}
.tb-sub{font-size:11px;color:rgba(255,255,255,.5);margin-top:1px;}
.content{max-width:760px;margin:0 auto;padding:24px 20px;display:flex;flex-direction:column;gap:20px;}
.card{background:#fff;border:0.5px solid var(--border);border-radius:12px;overflow:hidden;}
.card-head{padding:16px 20px;border-bottom:0.5px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.card-title{font-size:13px;font-weight:600;}
.card-body{padding:20px;}
.user-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:0.5px solid #F5F3FA;}
.user-row:last-child{border-bottom:none;}
.user-name{font-size:13px;font-weight:500;}
.user-email{font-size:11px;color:var(--mist);margin-top:1px;}
.role-badge{font-size:10px;padding:3px 9px;border-radius:20px;font-weight:600;}
.rb-admin{background:rgba(28,43,74,.1);color:var(--navy);}
.rb-manager{background:var(--green-bg);color:var(--green);}
.rb-receiver{background:#E6F1FB;color:#1A6FAD;}
.rb-hospital_manager{background:#EEE8F5;color:var(--purple);}
.rb-inventory_lead{background:#FEF3E2;color:var(--amber);}
.field{display:flex;flex-direction:column;gap:5px;margin-bottom:14px;}
label{font-size:11px;font-weight:600;color:var(--mist);text-transform:uppercase;letter-spacing:.04em;}
input,select{padding:10px 12px;border:0.5px solid var(--border);border-radius:9px;font-size:14px;font-family:'DM Sans',sans-serif;width:100%;background:#fff;color:var(--navy);}
input:focus,select:focus{outline:none;border-color:var(--navy);}
.btn-primary{width:100%;padding:12px;background:var(--navy);color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;margin-top:4px;}
.btn-primary:hover{opacity:.9;}
.msg{padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:12px;display:none;}
.msg.success{background:var(--green-bg);color:var(--green);border:0.5px solid #B0D8C0;display:block;}
.msg.error{background:var(--red-bg);color:var(--red);border:0.5px solid #F0AAAA;display:block;}
.empty{color:var(--mist);font-size:12px;padding:12px 0;text-align:center;}
.nav{display:none;}
</style>
</head>
<body>
<div class="topbar">
  <div>
    <div class="tb-title">Manage Users</div>
    <div class="tb-sub" id="tb-sub">Loading…</div>
  </div>
</div>
<div class="content">

  <!-- Create user -->
  <div class="card">
    <div class="card-head">
      <div class="card-title">Create new user</div>
    </div>
    <div class="card-body">
      <div id="msg" class="msg"></div>
      <div class="field">
        <label>Full name</label>
        <input id="new-name" type="text" placeholder="First name Last name…">
      </div>
      <div class="field">
        <label>Email</label>
        <input id="new-email" type="email" placeholder="name@scout.vet">
      </div>
      <div class="field">
        <label>Temporary password</label>
        <input id="new-pass" type="text" value="MedSync2026!" autocomplete="off">
      </div>
      <div class="field">
        <label>Role</label>
        <select id="new-role">
          <!-- Options populated by JS based on logged-in role -->
        </select>
      </div>
      <div class="field" id="loc-field" style="display:none;">
        <label>Location</label>
        <select id="new-loc"></select>
      </div>
      <button class="btn-primary" onclick="createUser()">Create user →</button>
    </div>
  </div>

  <!-- Existing users -->
  <div class="card">
    <div class="card-head">
      <div class="card-title">Current users</div>
    </div>
    <div class="card-body" id="user-list">
      <div class="empty">Loading…</div>
    </div>
  </div>

</div>

<script>
const SUPA_URL = 'https://aemkdummdrmxtwrkggjw.supabase.co';
const SUPA_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlbWtkdW1tZHJteHR3cmtnZ2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAwOTQwNjEsImV4cCI6MjA5NTY3MDA2MX0.JzUojqfs9K6wOtrhjDnQ_knVU1wDvqR0MFH9z_r4G4s';
const _sess = (function(){ try { return JSON.parse(localStorage.getItem('medsync_session') || '{}'); } catch(e) { return {}; } })();
const H = { 'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + (_sess.access_token || SUPA_KEY), 'Content-Type': 'application/json' };

let myRole = 'manager';
const ROLE_LABELS = {
  admin: 'Admin', manager: 'Manager', hospital_manager: 'H. Manager',
  receiver: 'Receiver', inventory_lead: 'Inventory Lead'
};
// Roles each role can create
const CREATABLE = {
  admin:   ['admin','manager','hospital_manager','receiver','inventory_lead'],
  manager: ['receiver','inventory_lead']
};

async function boot() {
  try {
    const mu = JSON.parse(localStorage.getItem('medsync_user') || '{}');
    myRole = mu.role || 'manager';
    document.getElementById('tb-sub').textContent =
      'User Management · ' + (mu.full_name || '');

    // Populate role options
    const roleSel = document.getElementById('new-role');
    const allowed = CREATABLE[myRole] || CREATABLE['manager'];
    roleSel.innerHTML = allowed.map(r =>
      `<option value="${r}">${ROLE_LABELS[r] || r}</option>`
    ).join('');

    roleSel.addEventListener('change', onRoleChange);
    onRoleChange();

    // Load locations for manager/receiver roles
    const locRes = await fetch(SUPA_URL + '/rest/v1/locations?select=id,name&order=name', { headers: H });
    const locs = await locRes.json();
    const locSel = document.getElementById('new-loc');
    if (Array.isArray(locs)) {
      locSel.innerHTML = locs.map(l => `<option value="${l.id}">${l.name}</option>`).join('');
    }

    await loadUsers();
  } catch(e) {
    console.error(e);
  }
}

function onRoleChange() {
  const role = document.getElementById('new-role').value;
  const showLoc = ['manager','receiver','inventory_lead'].includes(role);
  document.getElementById('loc-field').style.display = showLoc ? 'block' : 'none';
}

async function loadUsers() {
  const res = await fetch(SUPA_URL + '/rest/v1/users?select=id,full_name,email,role&order=role,full_name', { headers: H });
  const users = await res.json();
  const el = document.getElementById('user-list');
  if (!Array.isArray(users) || users.length === 0) {
    el.innerHTML = '<div class="empty">No users found.</div>';
    return;
  }
  el.innerHTML = users.map(u => `
    <div class="user-row">
      <div>
        <div class="user-name">${u.full_name || '—'}</div>
        <div class="user-email">${u.email || ''}</div>
      </div>
      <span class="role-badge rb-${u.role}">${ROLE_LABELS[u.role] || u.role}</span>
    </div>
  `).join('');
}

async function createUser() {
  const name  = document.getElementById('new-name').value.trim();
  const email = document.getElementById('new-email').value.trim();
  const pass  = document.getElementById('new-pass').value.trim();
  const role  = document.getElementById('new-role').value;
  const msg   = document.getElementById('msg');

  if (!name || !email || !pass) {
    showMsg('Please fill in all fields.', 'error'); return;
  }

  try {
    // Sign up via Supabase auth
    const signRes = await fetch(SUPA_URL + '/auth/v1/signup', {
      method: 'POST',
      headers: { 'apikey': SUPA_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: pass })
    });
    const signData = await signRes.json();
    const userId = signData.id || (signData.user && signData.user.id);

    if (!userId) {
      showMsg('Auth signup failed: ' + (signData.msg || signData.message || JSON.stringify(signData)), 'error');
      return;
    }

    // Insert into users table
    await fetch(SUPA_URL + '/rest/v1/users', {
      method: 'POST',
      headers: { ...H, 'Prefer': 'return=minimal' },
      body: JSON.stringify({ id: userId, email, full_name: name, role })
    });

    showMsg(name + ' created successfully as ' + (ROLE_LABELS[role] || role) + '.', 'success');
    document.getElementById('new-name').value = '';
    document.getElementById('new-email').value = '';
    document.getElementById('new-pass').value = 'MedSync2026!';
    await loadUsers();
  } catch(e) {
    showMsg('Error: ' + e.message, 'error');
  }
}

function showMsg(text, type) {
  const el = document.getElementById('msg');
  el.textContent = text;
  el.className = 'msg ' + type;
}

boot();
</script>
</body>
</html>'''

with open(f'{BASE}/medsync_users_live.html', 'w', encoding='utf-8') as f:
    f.write(users_html)
print('OK: medsync_users_live.html created')

print('\nDone. Also run this SQL to add inventory_lead to the role constraint:')
print("""
ALTER TABLE users DROP CONSTRAINT users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
CHECK (role IN ('admin','manager','hospital_manager','receiver','inventory_lead'));
""")
