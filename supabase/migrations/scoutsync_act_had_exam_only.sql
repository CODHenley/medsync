-- ══════════════════════════════════════════════════════════════
-- ScoutSync — ACT: count cases (had_exam), not every encounter row
-- Run in: Supabase Dashboard → SQL Editor
--
-- v_avg_transaction_charge_daily and v_act_per_provider_daily both divide
-- total revenue by a raw count of encounters with a non-null started_at --
-- with no had_exam filter. A client who only stops by to pick up something
-- like canned dog food (no doctor exam involved) still gets logged as an
-- encounter in Vetspire, which inflates the transaction count without
-- being a real clinical case, silently distorting ACT away from what it's
-- meant to answer: "how much revenue per real visit." Every other case-based
-- metric on this dashboard (heatmaps, case volume, ramp-up chart) already
-- uses had_exam as the one canonical "case" definition -- ACT's denominator
-- should match it instead of using a different, looser definition.
--
-- Total revenue itself is untouched by this -- retail/pharmacy pickups are
-- real money and should stay in the top-line revenue numbers. This only
-- changes what counts as a "transaction" in the revenue ÷ transactions
-- division.
-- ══════════════════════════════════════════════════════════════

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
  where started_at is not null and had_exam
  group by location_id, date(started_at)
) e on e.location_id = r.location_id and e.visit_date = r.service_date;

create or replace view public.v_act_per_provider_daily as
select
  r.provider_id,
  r.location_id,
  r.service_date,
  r.revenue,
  coalesce(e.encounter_count, 0) as encounter_count
from (
  select provider_id, location_id, service_date, sum(amount) as revenue
  from public.invoice_line_items
  where provider_id is not null
  group by provider_id, location_id, service_date
) r
left join (
  select provider_id, location_id, date(started_at) as visit_date, count(*) as encounter_count
  from public.encounters
  where started_at is not null and provider_id is not null and had_exam
  group by provider_id, location_id, date(started_at)
) e
  on e.provider_id = r.provider_id
 and e.location_id = r.location_id
 and e.visit_date  = r.service_date;
