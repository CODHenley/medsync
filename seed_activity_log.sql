-- MedSync Activity Log Seed Data — Pitch Demo
-- Run in: Supabase → SQL Editor → New Query → Paste → Run
-- Uses name lookups so no UUID hunting required.
-- Safe to re-run: uses INSERT (will add duplicates if run twice — only run once)

INSERT INTO activity_log (location_id, event_type, description, reference_id, flag, metadata, created_at)
VALUES

-- ── Lincoln Park ─────────────────────────────────────────────────────────────
(
  (SELECT id FROM locations WHERE name = 'Lincoln Park'),
  'order', 'Weekly order submitted — 14 SKUs',
  'PO-2026-0528-1142', 'ok',
  '{"skus": 14, "total": 1847.32, "submitted_at": "11:42 AM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '8 days'
),
(
  (SELECT id FROM locations WHERE name = 'Lincoln Park'),
  'receive', 'PO received — 13 of 14 items confirmed',
  'PO-2026-0528-1142', 'warn',
  '{"items_expected": 14, "items_received": 13, "missing_item": "Buprenorphine 0.3mg/ml", "received_by": "Alex M."}'::jsonb,
  NOW() - INTERVAL '6 days'
),
(
  (SELECT id FROM locations WHERE name = 'Lincoln Park'),
  'goods', 'Goods lost submitted — Ketamine HCl 10mg/ml',
  NULL, 'warn',
  '{"product": "Ketamine HCl 10mg/ml", "category": "Expired product", "qty": 2, "value": 284.00, "submitted_by": "Alex M."}'::jsonb,
  NOW() - INTERVAL '5 days'
),
(
  (SELECT id FROM locations WHERE name = 'Lincoln Park'),
  'order', 'Weekly order submitted — 11 SKUs',
  'PO-2026-0604-0958', 'ok',
  '{"skus": 11, "total": 1423.60, "submitted_at": "9:58 AM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '1 day'
),

-- ── Old Orchard ──────────────────────────────────────────────────────────────
(
  (SELECT id FROM locations WHERE name = 'Old Orchard'),
  'order', 'Weekly order submitted — 9 SKUs',
  'PO-2026-0528-1318', 'ok',
  '{"skus": 9, "total": 1102.45, "submitted_at": "1:18 PM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '8 days'
),
(
  (SELECT id FROM locations WHERE name = 'Old Orchard'),
  'order', 'Weekly order submitted late — 12 SKUs',
  'PO-2026-0521-1347', 'warn',
  '{"skus": 12, "total": 1688.90, "submitted_at": "1:47 PM", "late": true, "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '15 days'
),
(
  (SELECT id FROM locations WHERE name = 'Old Orchard'),
  'receive', 'PO received — 9 of 9 items confirmed',
  'PO-2026-0528-1318', 'ok',
  '{"items_expected": 9, "items_received": 9, "received_by": "Casey R."}'::jsonb,
  NOW() - INTERVAL '6 days'
),
(
  (SELECT id FROM locations WHERE name = 'Old Orchard'),
  'goods', 'Goods lost submitted — Maropitant Citrate 10mg/ml',
  NULL, 'ok',
  '{"product": "Maropitant Citrate 10mg/ml", "category": "Damaged / Spilled", "qty": 1, "value": 84.20, "note": "Vial dropped during draw", "submitted_by": "Jamie K."}'::jsonb,
  NOW() - INTERVAL '4 days'
),
(
  (SELECT id FROM locations WHERE name = 'Old Orchard'),
  'goods', 'Goods lost submitted — Ondansetron 2mg/ml',
  NULL, 'warn',
  '{"product": "Ondansetron 2mg/ml", "category": "Expired product", "qty": 3, "value": 115.20, "submitted_by": "Jamie K."}'::jsonb,
  NOW() - INTERVAL '2 days'
),

-- ── West Loop ────────────────────────────────────────────────────────────────
(
  (SELECT id FROM locations WHERE name = 'West Loop'),
  'order', 'Weekly order submitted — 16 SKUs',
  'PO-2026-0528-1055', 'ok',
  '{"skus": 16, "total": 2241.75, "submitted_at": "10:55 AM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '8 days'
),
(
  (SELECT id FROM locations WHERE name = 'West Loop'),
  'receive', 'PO received — 16 of 16 items confirmed',
  'PO-2026-0528-1055', 'ok',
  '{"items_expected": 16, "items_received": 16, "received_by": "Alex M."}'::jsonb,
  NOW() - INTERVAL '6 days'
),
(
  (SELECT id FROM locations WHERE name = 'West Loop'),
  'goods', 'Goods lost submitted — Gabapentin 100mg caps',
  NULL, 'ok',
  '{"product": "Gabapentin 100mg caps", "category": "Medication waste", "qty": 12, "value": 11.64, "note": "Partial blister packs after discharge", "submitted_by": "Alex M."}'::jsonb,
  NOW() - INTERVAL '3 days'
),
(
  (SELECT id FROM locations WHERE name = 'West Loop'),
  'goods', 'Goods lost submitted — Hydromorphone 2mg/ml',
  NULL, 'warn',
  '{"product": "Hydromorphone 2mg/ml", "category": "Controlled Substances (DEA)", "qty": 1, "value": 218.00, "note": "DEA waste log #WL-0604-01 filed", "submitted_by": "Alex M."}'::jsonb,
  NOW() - INTERVAL '1 day'
),
(
  (SELECT id FROM locations WHERE name = 'West Loop'),
  'order', 'Weekly order submitted — 13 SKUs',
  'PO-2026-0604-1047', 'ok',
  '{"skus": 13, "total": 1914.20, "submitted_at": "10:47 AM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '1 day'
),

-- ── Wheaton ──────────────────────────────────────────────────────────────────
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'order', 'Weekly order submitted — 8 SKUs',
  'PO-2026-0528-1229', 'ok',
  '{"skus": 8, "total": 892.10, "submitted_at": "12:29 PM", "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '8 days'
),
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'receive', 'PO received — 8 of 8 items confirmed',
  'PO-2026-0528-1229', 'ok',
  '{"items_expected": 8, "items_received": 8, "received_by": "Casey R."}'::jsonb,
  NOW() - INTERVAL '5 days'
),
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'order', 'Weekly order submitted late — 10 SKUs',
  'PO-2026-0604-1312', 'warn',
  '{"skus": 10, "total": 1340.80, "submitted_at": "1:12 PM", "late": true, "vendor": "MWI Animal Health"}'::jsonb,
  NOW() - INTERVAL '1 day'
),
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'goods', 'Goods lost submitted — Meloxicam 5mg/ml',
  NULL, 'ok',
  '{"product": "Meloxicam 5mg/ml", "category": "Expired product", "qty": 2, "value": 44.80, "submitted_by": "Casey R."}'::jsonb,
  NOW() - INTERVAL '3 days'
),
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'goods', 'Goods lost submitted — Tramadol 50mg tabs',
  NULL, 'ok',
  '{"product": "Tramadol 50mg tabs", "category": "In-house use", "qty": 6, "value": 7.44, "note": "Staff patient tx, not billed", "submitted_by": "Casey R."}'::jsonb,
  NOW() - INTERVAL '2 days'
),
(
  (SELECT id FROM locations WHERE name = 'Wheaton'),
  'user', 'Min/Max thresholds updated — 4 products adjusted for peak season',
  NULL, 'ok',
  '{"products_updated": 4, "updated_by": "Megan Henley", "season": "peak"}'::jsonb,
  NOW() - INTERVAL '10 days'
);
