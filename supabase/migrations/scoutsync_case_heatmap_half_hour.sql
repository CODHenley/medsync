-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Half-hour resolution for the Case Volume / Case Value heatmaps
-- Run in: Supabase Dashboard → SQL Editor
--
-- The heatmaps only ever exposed hour_of_day (0-23), so the grid could only
-- show one column per hour. Appointments are actually scheduled on the
-- half hour, so an hour-wide bucket blends two different scheduled slots
-- together and can't be compared against the schedule directly.
--
-- Fix: add minute_of_hour (Chicago local, same conversion as day_of_week/
-- hour_of_day) so the dashboard can derive a half-hour slot
-- (hour_of_day*2 + (minute_of_hour >= 30 ? 1 : 0)) client-side. Appended
-- as the LAST selected column, after chief_complaint (the current last
-- column, per scoutsync_invoice_total.sql -- NOT
-- scoutsync_case_heatmap_drilldown.sql's e.estimated_case_value, which
-- that later migration dropped from encounters entirely in favor of the
-- real e.invoice_total), not alongside the other extract(...) columns --
-- CREATE OR REPLACE VIEW only allows adding columns at the end of the
-- select list; inserting one in the middle shifts every later column's
-- ordinal position, which Postgres treats as an attempted rename of that
-- column (blocked with error 42P16 -- see scoutsync_rdvm_directory.sql
-- for where this was first hit live).
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                                              as encounter_id,
  e.started_at,
  extract(dow    from e.started_at at time zone 'America/Chicago')::int as day_of_week,   -- 0=Sunday .. 6=Saturday, Chicago local
  extract(hour   from e.started_at at time zone 'America/Chicago')::int as hour_of_day,   -- Chicago local hour
  e.invoice_total                                                   as case_value,
  e.chief_complaint,
  extract(minute from e.started_at at time zone 'America/Chicago')::int as minute_of_hour -- Chicago local minute, for half-hour buckets
from public.encounters e
where e.had_exam
  and e.started_at is not null;
