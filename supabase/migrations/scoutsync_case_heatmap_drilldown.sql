-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Add drill-down detail to the case heatmaps
-- Run in: Supabase Dashboard → SQL Editor
--
-- Clicking a heatmap cell needs more than day_of_week/hour_of_day/
-- case_value to show anything useful — adds chief_complaint (reason for
-- visit) and location_id (already selected, listed here for clarity) so
-- the dashboard can list the actual cases behind a cell without a second
-- query. No new columns -- both already exist on encounters.
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                                            as encounter_id,
  e.started_at,
  extract(dow  from e.started_at at time zone 'America/Chicago')::int as day_of_week,   -- 0=Sunday .. 6=Saturday, Chicago local
  extract(hour from e.started_at at time zone 'America/Chicago')::int as hour_of_day,   -- Chicago local hour
  e.estimated_case_value                                          as case_value,
  e.chief_complaint
from public.encounters e
where e.had_exam
  and e.started_at is not null;
