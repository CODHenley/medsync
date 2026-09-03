-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Avg Cost per Transaction (ACT), per provider, daily grain
-- Run in: Supabase Dashboard → SQL Editor
--
-- v_avg_transaction_charge_daily (the existing sitewide ACT view) is
-- location+day grain only -- no provider_id at all. This adds the
-- provider-level equivalent, needed for the new "Avg Cost per Transaction
-- by Provider" report (trailing N days / MTD / YTD / MoM / YoY / previous
-- year / custom range -- all computed client-side by summing this daily
-- grain over whichever date window a given cut needs).
--
-- Same join pattern as v_avg_transaction_charge_daily: invoice_line_items
-- holds Vetspire salesReport revenue totals, not a real invoice/transaction
-- count (Vetspire's salesReport has no invoice id), so "transactions" is
-- proxied by the encounter count already synced for that same
-- provider/location/day.
-- ══════════════════════════════════════════════════════════════

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
  where started_at is not null and provider_id is not null
  group by provider_id, location_id, date(started_at)
) e
  on e.provider_id = r.provider_id
 and e.location_id = r.location_id
 and e.visit_date  = r.service_date;
