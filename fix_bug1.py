import sys

path = '/Users/meganhenley/Downloads/medsync_deploy/index.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

OLD = "  showScreen('portfolio');\n})();"

NEW = (
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
    "  }\n"
    "})();"
)

if OLD not in src:
    print("ERROR: target string not found — no changes written.")
    sys.exit(1)

count = src.count(OLD)
if count > 1:
    print(f"ERROR: target string found {count} times — ambiguous, no changes written.")
    sys.exit(1)

patched = src.replace(OLD, NEW, 1)

# Verify critical CSS still present
if '.divider { height: 0.5px; background: #C8C4D8; margin: 4rem 0; }' not in patched:
    print("ERROR: critical CSS line 1 missing after patch — aborting.")
    sys.exit(1)
if '#app-content .divider' not in patched:
    print("ERROR: critical CSS line 2 missing after patch — aborting.")
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(patched)

print("Bug 1 patched successfully.")
print("Critical CSS verified present.")
