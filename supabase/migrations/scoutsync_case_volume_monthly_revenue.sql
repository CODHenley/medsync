-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Add total_revenue to v_case_volume_monthly
-- Run in: Supabase Dashboard → SQL Editor
--
-- Backs the new Scout De Novo tab's Revenue per Case chart (total_revenue /
-- case_count, monthly, re-anchored to months-since-opening the same way
-- the Ramp-Up chart already does for case_count alone). Reuses this view
-- rather than adding a new one, since it's the same location + month +
-- case grain already, one extra aggregate column.
--
-- total_revenue appended as the LAST selected column (after case_count),
-- not alongside it -- CREATE OR REPLACE VIEW only allows adding columns
-- at the end of the select list; inserting one earlier shifts every later
-- column's ordinal position, which Postgres treats as an attempted rename
-- (blocked with error 42P16 -- see scoutsync_rdvm_directory.sql for where
-- this was first hit live).
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_case_volume_monthly as
select
  e.location_id,
  date_trunc('month', e.started_at at time zone 'America/Chicago')::date as month_start,
  count(*) as case_count,
  sum(e.invoice_total) as total_revenue
from public.encounters e
where e.had_exam
  and e.started_at is not null
group by e.location_id, date_trunc('month', e.started_at at time zone 'America/Chicago');
