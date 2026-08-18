-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Financial: fix silent revenue duplication on re-sync
-- Run in: Supabase Dashboard → SQL Editor
--
-- invoice_line_items upserts on (location_id, provider_id, product_category_id,
-- service_date). When Vetspire's salesReport references a provider the clinical
-- sync hasn't loaded yet, provider_id lands as NULL — and Postgres never treats
-- NULL as equal to NULL in a unique constraint, so ON CONFLICT silently fails to
-- match on every later run. Every 4-hour re-sync of the same overlapping window
-- would insert a fresh duplicate row instead of updating, multiplying revenue
-- for any unattributed transactions over time.
--
-- Fix: a fixed sentinel provider row so provider_id is never actually NULL in
-- the upsert payload — same pattern already used for product_category_id's
-- '0 = uncategorized' default in scoutsync_financial_breakdown.sql.
-- ══════════════════════════════════════════════════════════════

insert into public.providers (id, vetspire_provider_id, full_name, provider_type, is_active)
values ('00000000-0000-0000-0000-000000000000', '__unattributed__', 'Unattributed / not yet synced', 'other', false)
on conflict (vetspire_provider_id) do nothing;
