-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Fix case dollar-value heatmap (was always $0)
-- Run in: Supabase Dashboard → SQL Editor
--
-- v_case_heatmap (scoutsync_case_maps_and_heatmaps.sql) computed case_value
-- via `left join invoice_line_items on invoice_line_items.encounter_id =
-- encounters.id` -- that join can never match anything. invoice_line_items
-- is populated by vetspire_financial_sync.py from Vetspire's salesReport,
-- which only breaks down by day/provider/product-category (confirmed via
-- vetspire_clinical_schema_probe.py); it has no per-encounter grain and
-- never sets encounter_id. salesReport also flatly rejects an
-- APPOINTMENT_TIME breakdown despite it appearing in ReportBreakdown's own
-- enum ("unprocessable_entity"), and its smallest segment is DAY -- so
-- salesReport has no time-of-day dimension at all, full stop.
--
-- Fix: vetspire_clinical_sync.py now computes estimated_case_value at sync
-- time, summing quantity * product.unitPrice across each encounter's own
-- encounterProducts (confirmed real, populated data -- e.g. "Exam - Urgent
-- Care" at $135.00). This is the catalog list price, NOT the final
-- invoiced/collected amount -- it won't reflect discounts, membership
-- pricing, taxes, or refunds. Labeled "estimated" everywhere it's shown,
-- same treatment as chief_complaint being labeled reason-for-visit rather
-- than diagnosis.
-- ══════════════════════════════════════════════════════════════

alter table public.encounters
  add column if not exists estimated_case_value numeric not null default 0;

comment on column public.encounters.estimated_case_value is
  'sum(quantity * product.unitPrice) across this encounter''s '
  'encounterProducts -- catalog list price, not the final invoiced/'
  'collected total (no discounts/membership pricing/taxes/refunds). '
  'The only per-encounter dollar figure Vetspire actually exposes; '
  'invoice_line_items has no per-encounter grain (see module note above).';

create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                          as encounter_id,
  e.started_at,
  extract(dow from e.started_at)::int           as day_of_week,   -- 0=Sunday .. 6=Saturday
  extract(hour from e.started_at)::int          as hour_of_day,
  e.estimated_case_value                        as case_value
from public.encounters e
where e.had_exam
  and e.started_at is not null;
