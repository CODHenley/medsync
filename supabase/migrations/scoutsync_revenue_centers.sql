-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Revenue centers (Radiographs / Inhouse laboratory / Treatments)
-- Run in: Supabase Dashboard → SQL Editor
--
-- Investigation into the "Uncategorized" bucket on Revenue by Source found
-- 97% of it ($539,758.90 of $556,660.67 over a 90-day sample) isn't a
-- product-categorization gap at all -- salesReport's PRODUCT_CATEGORY_ID
-- breakdown returns null for these rows because Vetspire bills imaging,
-- in-house lab work, and treatments as flat revenue-center-level charges
-- with no product record attached, not because any product needs
-- recategorizing. Confirmed live: re-querying with
-- breakdowns:[PROVIDER_ID, PRODUCT_CATEGORY_ID, REVENUE_CENTER_ID] returns
-- a real revenue_center_id (879/880/881) on exactly these null-category
-- rows, letting the dashboard show real names instead of one lump sum.
--
-- 0 is used as the "no revenue center" sentinel (same convention as
-- product_category_id's 0 = uncategorized) so the natural key below never
-- has to deal with NULL-vs-NULL uniqueness -- same bug class already fixed
-- once for provider_id in scoutsync_financial_unattributed_provider.sql.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.revenue_centers (
  id    integer primary key,
  name  text not null
);

alter table public.revenue_centers enable row level security;
drop policy if exists "anon_all" on public.revenue_centers;
create policy "anon_all" on public.revenue_centers for all to anon using (true) with check (true);

alter table public.invoice_line_items add column if not exists revenue_center_id integer not null default 0;

-- The old natural key (location_id, provider_id, product_category_id,
-- service_date) would silently collide: a provider/day can carry more than
-- one revenue-center row that all share product_category_id=0 (e.g. both a
-- Radiographs row and an Inhouse laboratory row), which the old key can't
-- tell apart. Replace it with a key that includes revenue_center_id.
drop index if exists idx_invoice_line_items_natural_key;
create unique index if not exists idx_invoice_line_items_natural_key
  on public.invoice_line_items(location_id, provider_id, product_category_id, revenue_center_id, service_date);

-- Rebuilt to carry revenue_center_id through so the dashboard can label a
-- product_category_id=0 row by its real revenue center instead of lumping
-- it into "Uncategorized".
drop view if exists public.v_financial_kpis_daily;

create view public.v_financial_kpis_daily as
select
  location_id,
  service_date,
  product_category_id,
  revenue_center_id,
  sum(amount) as revenue
from public.invoice_line_items
group by location_id, service_date, product_category_id, revenue_center_id;
