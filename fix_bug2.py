import sys

path = '/Users/meganhenley/Downloads/medsync_deploy/index.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

OLD = (
    "  if (name==='actlog' && window._actlogLoaded !== true) {\n"
    "    window._actlogLoaded = true;\n"
    "    if (typeof loadEvents === 'function') setTimeout(loadEvents, 100);\n"
    "  }\n"
    "}"
)

NEW = (
    "  if (name==='actlog' && window._actlogLoaded !== true) {\n"
    "    window._actlogLoaded = true;\n"
    "    if (typeof loadEvents === 'function') setTimeout(loadEvents, 100);\n"
    "  }\n"
    "  if (['order','receiving','goods'].indexOf(name) !== -1) {\n"
    "    try {\n"
    "      var mu = JSON.parse(localStorage.getItem('medsync_user') || '{}');\n"
    "      if (mu.role === 'manager' && mu.locations && mu.locations[0]) {\n"
    "        var locName = mu.locations[0].name;\n"
    "        var locSel = '#ms-' + name + ' iframe';\n"
    "        var locAttempts = 0;\n"
    "        var locTimer = setInterval(function() {\n"
    "          locAttempts++;\n"
    "          var locIframe = document.querySelector(locSel);\n"
    "          if (locIframe && locIframe.contentWindow) {\n"
    "            locIframe.contentWindow.postMessage({ type: 'setLocation', loc: locName }, '*');\n"
    "          }\n"
    "          if (locAttempts >= 10) clearInterval(locTimer);\n"
    "        }, 300);\n"
    "      }\n"
    "    } catch(e) {}\n"
    "  }\n"
    "}"
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

print("Bug 2 patched successfully.")
print("Critical CSS verified present.")
