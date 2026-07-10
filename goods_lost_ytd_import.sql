-- MedSync — Goods Lost YTD 2026 Snapshot Import
-- Source: 2026_Goods_Lost_Summary (Microsoft Form / Excel workbook)
-- Generated: 2026-07-10
-- One row per location per month; $0 months are omitted.
-- Run in Supabase SQL Editor.
--
-- Location UUIDs:
--   Lincoln Park : 11111111-0000-0000-0000-000000000001
--   Old Orchard  : 11111111-0000-0000-0000-000000000002
--   West Loop    : 11111111-0000-0000-0000-000000000003
--   Wheaton      : 11111111-0000-0000-0000-000000000004

-- Step 1: Remove any existing snapshot import rows for Jan–Jul 2026
-- (safe to re-run; won't touch rows entered via the Goods Lost form)
DELETE FROM goods_lost
WHERE product_name = 'Monthly Summary Import'
  AND created_at >= '2026-01-01'
  AND created_at <  '2026-08-01';

-- Step 2: Insert monthly summary rows
INSERT INTO goods_lost (location_id, product_name, category, value_lost, created_at)
VALUES
  -- ── Lincoln Park ──────────────────────────────────────────────
  ('11111111-0000-0000-0000-000000000001', 'Monthly Summary Import', 'Summary Import', 314.96,  '2026-01-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000001', 'Monthly Summary Import', 'Summary Import', 249.60,  '2026-02-28T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000001', 'Monthly Summary Import', 'Summary Import', 139.11,  '2026-03-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000001', 'Monthly Summary Import', 'Summary Import', 328.21,  '2026-04-30T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000001', 'Monthly Summary Import', 'Summary Import', 205.96,  '2026-05-31T23:59:00Z'),

  -- ── West Loop ─────────────────────────────────────────────────
  ('11111111-0000-0000-0000-000000000003', 'Monthly Summary Import', 'Summary Import', 1178.52, '2026-01-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000003', 'Monthly Summary Import', 'Summary Import', 271.16,  '2026-02-28T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000003', 'Monthly Summary Import', 'Summary Import', 122.18,  '2026-03-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000003', 'Monthly Summary Import', 'Summary Import', 263.75,  '2026-04-30T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000003', 'Monthly Summary Import', 'Summary Import', 5.35,    '2026-07-07T23:59:00Z'),

  -- ── Old Orchard ───────────────────────────────────────────────
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 1232.60, '2026-01-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 418.98,  '2026-02-28T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 600.10,  '2026-03-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 204.74,  '2026-04-30T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 632.28,  '2026-05-31T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000002', 'Monthly Summary Import', 'Summary Import', 772.02,  '2026-06-30T23:59:00Z'),

  -- ── Wheaton ───────────────────────────────────────────────────
  -- Jan–May: no data recorded in source workbook
  ('11111111-0000-0000-0000-000000000004', 'Monthly Summary Import', 'Summary Import', 114.53,  '2026-06-30T23:59:00Z'),
  ('11111111-0000-0000-0000-000000000004', 'Monthly Summary Import', 'Summary Import', 16.57,   '2026-07-07T23:59:00Z');

-- Verify row counts per location
SELECT
  location_id,
  COUNT(*)       AS months_imported,
  SUM(value_lost) AS total_imported
FROM goods_lost
WHERE product_name = 'Monthly Summary Import'
  AND created_at >= '2026-01-01'
GROUP BY location_id
ORDER BY location_id;
