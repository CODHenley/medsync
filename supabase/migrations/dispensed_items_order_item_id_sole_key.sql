-- ══════════════════════════════════════════════════════════════
-- dispensed_items — make order_item_id the ONE natural key
-- Run in: Supabase Dashboard → SQL Editor
--
-- Prior migration (dispensed_items_order_id_migration.sql) added order_item_id
-- with a PARTIAL unique index (..., location_id) WHERE order_item_id IS NOT NULL.
-- PostgREST's on_conflict=col1,col2 generates plain ON CONFLICT(col1,col2) with
-- no WHERE clause, which Postgres can only use to infer a NON-partial unique
-- index/constraint. Every sync/backfill script since then silently fell back
-- to hand-rolled day/month aggregation instead (there was no working
-- on_conflict target to use) — the direct cause of the Aug 2026 double-count
-- incident (2,138 duplicate rows from two backfills disagreeing on
-- granularity).
--
-- Fix: a FULL (non-partial) unique index on (order_item_id, location_id).
-- Postgres treats every NULL as distinct in a unique index, so this is safe
-- with the existing legacy rows that still have order_item_id = NULL (the
-- Jan-Apr month-aggregated rows) — they don't collide with each other or
-- with anything else. PostgREST CAN infer a full index from the column list,
-- so on_conflict=order_item_id,location_id now actually works.
-- ══════════════════════════════════════════════════════════════

drop index if exists idx_dispensed_items_order_item_loc;
drop index if exists idx_dispensed_items_legacy_key;

create unique index if not exists idx_dispensed_items_order_item_id_loc
  on public.dispensed_items(order_item_id, location_id);
