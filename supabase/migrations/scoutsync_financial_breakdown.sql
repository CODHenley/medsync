-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Financial: relax invoice_line_items for real salesReport data
-- Run in: Supabase Dashboard → SQL Editor
--
-- salesReport (confirmed via vetspire_clinical_schema_probe.py, segment=DAY)
-- returns pre-aggregated daily totals per breakdown dimension (provider,
-- product category, ...), not individual invoices — there is no invoice id
-- and no fixed 4-bucket category. This loosens the original schema (which
-- assumed real invoice-level data) to match what Vetspire actually returns.
-- ══════════════════════════════════════════════════════════════

alter table public.invoice_line_items drop constraint if exists invoice_line_items_category_check;
alter table public.invoice_line_items alter column category drop not null;
alter table public.invoice_line_items alter column category drop default;

-- Vetspire's numeric product_category_id — 0 is used as the "uncategorized"
-- sentinel (salesReport returns a null category for miscellaneous charges)
-- so the natural key below never has to deal with NULL-vs-NULL uniqueness.
alter table public.invoice_line_items add column if not exists product_category_id integer not null default 0;

-- No natural vetspire_invoice_id exists for these aggregated rows — the
-- natural key is the combination of dimensions + day, one row per
-- location/provider/category/day.
create unique index if not exists idx_invoice_line_items_natural_key
  on public.invoice_line_items(location_id, provider_id, product_category_id, service_date);


-- ─────────────────────────────────────────────────────────────
-- Views — rebuilt against product_category_id (category/vetspire_invoice_id
-- are no longer populated: no fixed category bucket and no invoice id exist
-- in salesReport's aggregated rows)
-- ─────────────────────────────────────────────────────────────

-- CREATE OR REPLACE can't remove columns (category/invoice_count/
-- avg_transaction_charge existed on the old version of this view) — drop
-- it outright first.
drop view if exists public.v_financial_kpis_daily;

create view public.v_financial_kpis_daily as
select
  location_id,
  service_date,
  product_category_id,
  sum(amount) as revenue
from public.invoice_line_items
group by location_id, service_date, product_category_id;

-- Average Cost per Transaction (ACT): salesReport gives revenue totals, not
-- invoice counts, so ACT = revenue ÷ the encounter count already synced for
-- that same location/day. View name kept as v_avg_transaction_charge_daily
-- (schema/column names unchanged — this is a display-terminology rename).
create or replace view public.v_avg_transaction_charge_daily as
select
  r.location_id,
  r.service_date,
  r.revenue,
  e.encounter_count,
  r.revenue / nullif(e.encounter_count, 0) as avg_transaction_charge
from (
  select location_id, service_date, sum(amount) as revenue
  from public.invoice_line_items
  group by location_id, service_date
) r
left join (
  select location_id, date(started_at) as visit_date, count(*) as encounter_count
  from public.encounters
  where started_at is not null
  group by location_id, date(started_at)
) e on e.location_id = r.location_id and e.visit_date = r.service_date;
