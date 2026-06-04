import sys, os

path = '/sessions/peaceful-confident-bell/mnt/medsync_deploy/index.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Fix B: Wrap the orphaned CSS block in @media (max-width: 700px)
# The block sits outside any media query and applies grid rules to ALL screen sizes
OLD = (
    "}\n"
    "  /* Location rows — card style */\n"
    "  .tbl-row {\n"
    "    grid-template-columns: 1fr 1fr !important;\n"
    "    padding: 12px 16px !important;\n"
    "    gap: 6px 8px !important;\n"
    "    row-gap: 6px !important;\n"
    "  }\n"
    "\n"
    "  /* First col (name) spans full width */\n"
    "  .tbl-row > div:first-child {\n"
    "    grid-column: 1 / -1 !important;\n"
    "    border-bottom: 0.5px solid #E4E0F0;\n"
    "    padding-bottom: 6px;\n"
    "    margin-bottom: 2px;\n"
    "  }\n"
    "\n"
    "  /* All spans get labels via ::before */\n"
    "  .tbl-row > span { font-size: 13px !important; }\n"
    "\n"
    "  /* Metric grid — 2 cols on mobile */\n"
    "  .metric-grid { grid-template-columns: repeat(2, 1fr) !important; }\n"
    "  .metric { padding: 14px !important; }\n"
    "  .metric-value { font-size: 22px !important; }\n"
    "}"
)

NEW = (
    "}\n"
    "@media (max-width: 700px) {\n"
    "  /* Location rows — card style */\n"
    "  .tbl-row {\n"
    "    grid-template-columns: 1fr 1fr !important;\n"
    "    padding: 12px 16px !important;\n"
    "    gap: 6px 8px !important;\n"
    "    row-gap: 6px !important;\n"
    "  }\n"
    "\n"
    "  /* First col (name) spans full width */\n"
    "  .tbl-row > div:first-child {\n"
    "    grid-column: 1 / -1 !important;\n"
    "    border-bottom: 0.5px solid #E4E0F0;\n"
    "    padding-bottom: 6px;\n"
    "    margin-bottom: 2px;\n"
    "  }\n"
    "\n"
    "  /* All spans get labels via ::before */\n"
    "  .tbl-row > span { font-size: 13px !important; }\n"
    "\n"
    "  /* Metric grid — 2 cols on mobile */\n"
    "  .metric-grid { grid-template-columns: repeat(2, 1fr) !important; }\n"
    "  .metric { padding: 14px !important; }\n"
    "  .metric-value { font-size: 22px !important; }\n"
    "}"
)

if OLD not in src:
    print('ERROR: orphaned block not found')
    sys.exit(1)
if src.count(OLD) > 1:
    print('ERROR: multiple matches')
    sys.exit(1)

patched = src.replace(OLD, NEW, 1)

# Verify critical CSS
if '.divider { height: 0.5px; background: #C8C4D8; margin: 4rem 0; }' not in patched:
    print('ERROR: critical CSS missing after patch')
    sys.exit(1)
if '#app-content .divider' not in patched:
    print('ERROR: critical CSS line 2 missing')
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(patched)

print('OK: index.html — orphaned CSS block wrapped in @media (max-width: 700px)')
print('Critical CSS verified.')
