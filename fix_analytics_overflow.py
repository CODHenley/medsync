"""
Fix analytics mobile overflow:
1. Remove the bad `kpi-row { repeat(3,1fr) }` override (copy-paste from lifecycle)
2. Add a final, authoritative CSS block that hard-constrains all containers
3. Hide `.card-sub` in the COGs card header on mobile (too long — "Target: 8–10%…")
"""

BASE = '/sessions/peaceful-confident-bell/mnt/medsync_deploy'
path = f'{BASE}/medsync_analytics_live.html'

with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Remove the wrong kpi-row override (Lot lifecycle comment, wrong file) ──
OLD_LOT_OVERRIDE = (
    "\n  /* Lot lifecycle KPI: 3 cols */\n"
    "  .kpi-row { grid-template-columns: repeat(3, 1fr) !important; }\n"
)
if OLD_LOT_OVERRIDE in src:
    src = src.replace(OLD_LOT_OVERRIDE, "\n", 1)
    print("OK: removed bad kpi-row repeat(3) override")
else:
    print("WARNING: kpi-row repeat(3) override not found — check manually")

# ── 2. Add final authoritative mobile overflow fix ────────────────────────────
FINAL_CSS = """
/* ── FINAL: hard-constrain all containers to viewport width ── */
@media (max-width: 768px) {
  html, body {
    overflow-x: hidden !important;
    max-width: 100vw !important;
    width: 100% !important;
  }
  .outer, .right, .body-split, .main-col {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
  }
  .kpi-row {
    width: 100% !important;
    max-width: 100% !important;
    grid-template-columns: repeat(2, 1fr) !important;
    box-sizing: border-box !important;
  }
  .kpi {
    width: 100% !important;
    min-width: 0 !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
  }
  .card, .card-head, .bar-chart, .rev-grid {
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
  }
  /* Hide the long "Target: 8–10%…" subtitle on mobile — no room */
  .card-head .card-sub {
    display: none !important;
  }
  /* Revenue grid: 2×2 */
  .rev-grid {
    grid-template-columns: repeat(2, 1fr) !important;
    overflow: hidden !important;
  }
}
"""

# Insert just before </style>
if FINAL_CSS in src:
    print("WARNING: final CSS block already present — skipping")
elif '</style>' in src:
    src = src.replace('</style>', FINAL_CSS + '</style>', 1)
    print("OK: inserted final overflow-constraint CSS")
else:
    print("ERROR: </style> not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print("Done.")
