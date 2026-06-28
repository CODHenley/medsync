-- 2026 YTD Vetcove supplier spend — Lincoln Park, Old Orchard, West Loop
-- One row per supplier per location. purchased_at = 2026-06-28 (YTD snapshot date).
-- source = 'vetcove' so COGs bars can query this separately from manual external purchases.
-- Run in Supabase SQL editor.

-- Remove any prior Vetcove YTD snapshots for these three locations so re-runs are idempotent
DELETE FROM purchase_history
WHERE source = 'vetcove'
  AND location_id IN (
    '11111111-0000-0000-0000-000000000001',
    '11111111-0000-0000-0000-000000000002',
    '11111111-0000-0000-0000-000000000003'
  );

INSERT INTO purchase_history (location_id, vendor, amount, purchased_at, source, note, period_month)
VALUES

-- ── Lincoln Park ($97,630.99) ───────────────────────────────────────────────
('11111111-0000-0000-0000-000000000001', 'Idexx',                 47864.90, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Covetrus',              23935.37, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'MWI',                   10499.05, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Midwest',                6599.75, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Zoetis',                 2939.25, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Wedgewood Pharmacy',     1645.25, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Boehringer Ingelheim',   1580.17, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Amatheon',               1298.17, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Elanco',                  558.23, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Patterson',               441.89, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Royal Canin',             167.76, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Pharmsource AH',           94.50, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000001', 'Vetcove',                   6.70, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),

-- ── Old Orchard ($99,400.84) ────────────────────────────────────────────────
('11111111-0000-0000-0000-000000000002', 'Idexx',                 43773.75, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Patterson',             16922.54, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Pharmsource AH',        10422.55, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'MWI',                    9527.47, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Covetrus',               4865.34, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Amatheon',               4705.80, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Midwest',                4296.87, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Boehringer Ingelheim',   2515.18, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Wedgewood Pharmacy',     1695.20, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000002', 'Vetcove',                 676.14, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),

-- ── West Loop ($57,662.84) ──────────────────────────────────────────────────
('11111111-0000-0000-0000-000000000003', 'Idexx',                 27208.39, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Covetrus',               7740.55, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'MWI',                    6000.89, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Zoetis',                 5380.56, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Midwest',                3134.10, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Pharmsource AH',         2974.47, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Patterson',              1793.68, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Wedgewood Pharmacy',     1316.77, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Amatheon',               1052.40, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Vetcove',                 521.67, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Boehringer Ingelheim',    480.36, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06'),
('11111111-0000-0000-0000-000000000003', 'Medline',                  59.00, '2026-06-28', 'vetcove', '2026 YTD Vetcove supplier spend', '2026-06');
