-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Use the real invoice total, not an encounterProducts estimate
-- Run in: Supabase Dashboard → SQL Editor
--
-- User correction: the case-value heatmap should reflect "the total value
-- of that invoice where an exam was performed," not the price of the exam
-- line item alone. estimated_case_value summed quantity *
-- product.unitPrice across encounterProducts -- a live comparison of 15
-- real encounters (via vetspire_clinical_schema_probe.py) showed this
-- undercounting nearly every one: $135 (the exam alone) vs. a real
-- $717.00, $447.27, or $1,148.50 order total, and $0 vs. a real $410.92 for
-- one encounter whose encounterProducts didn't include a priced item at
-- all. encounterProducts is simply not reliably the complete set of
-- billed items for a visit.
--
-- Encounter.order: Order (a direct field, never queried before) is the
-- actual invoice, with a real totalAfterTaxCents. vetspire_clinical_sync.py
-- now writes that (divided to dollars) instead. VOID/DELETED orders count
-- as $0 (confirmed real InvoiceStatus values -- never actually charged);
-- PAID/DUE/OPEN/COLLECTIONS/UNCOLLECTIBLE all count as their real billed
-- amount regardless of payment status.
--
-- estimated_case_value is dropped, not kept alongside invoice_total --
-- carrying two competing "value of this case" columns would just invite
-- them to silently disagree later.
-- ══════════════════════════════════════════════════════════════

alter table public.encounters
  add column if not exists invoice_total numeric not null default 0;

comment on column public.encounters.invoice_total is
  'Real invoice total for this encounter (Order.totalAfterTaxCents / 100) '
  '-- confirmed via vetspire_clinical_schema_probe.py against live data, '
  'not derived/estimated from encounterProducts. VOID/DELETED orders are 0.';

alter table public.encounters drop column if exists estimated_case_value;

create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                                            as encounter_id,
  e.started_at,
  extract(dow  from e.started_at at time zone 'America/Chicago')::int as day_of_week,   -- 0=Sunday .. 6=Saturday, Chicago local
  extract(hour from e.started_at at time zone 'America/Chicago')::int as hour_of_day,   -- Chicago local hour
  e.invoice_total                                                 as case_value,
  e.chief_complaint
from public.encounters e
where e.had_exam
  and e.started_at is not null;
