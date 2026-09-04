-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Monthly case volume, per location
-- Run in: Supabase Dashboard → SQL Editor
--
-- Backs two dashboard charts: (1) "Case Volume Over Time" (seasonal
-- trend, year-over-year overlay) and (2) the de novo ramp-up chart
-- (case volume re-anchored to months-since-open per location). Both
-- just need location + month + count, so one small pre-aggregated view
-- avoids fetching years of raw per-encounter rows client-side the way
-- the heatmaps do (fine for a single selected range, too much for
-- multi-year history across 4 locations).
--
-- Same case definition (had_exam, started_at not null) and Chicago
-- local time convention as v_case_heatmap/v_case_geo (see
-- scoutsync_case_heatmap_local_time.sql) so a case is never bucketed
-- into the wrong calendar month here vs. counted differently elsewhere.
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_case_volume_monthly as
select
  e.location_id,
  date_trunc('month', e.started_at at time zone 'America/Chicago')::date as month_start,
  count(*) as case_count
from public.encounters e
where e.had_exam
  and e.started_at is not null
group by e.location_id, date_trunc('month', e.started_at at time zone 'America/Chicago');
