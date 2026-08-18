-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Financial: real product category names
-- Run in: Supabase Dashboard → SQL Editor
--
-- invoice_line_items.product_category_id is Vetspire's raw numeric category
-- id — the Financial tab was showing "Category 4949" instead of a real name.
-- Confirmed via vetspire_clinical_schema_probe.py that Vetspire's
-- productCategories root query returns real names (IDEXX In-house, Vaccines -
-- Canine, Radiology, ...) for all 18 categories in use. This is a small,
-- practice-wide reference list — synced by vetspire_financial_sync.py on
-- every run, upserted so a rename in Vetspire is picked up automatically.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.product_categories (
  id   integer primary key,
  name text not null
);

alter table public.product_categories enable row level security;
drop policy if exists "anon_all" on public.product_categories;
create policy "anon_all" on public.product_categories for all to anon using (true) with check (true);
