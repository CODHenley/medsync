-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Fix heatmap/geo day-of-week, hour-of-day, and visit_date:
-- were computed in the database session's timezone (UTC), not the
-- practice's actual local time
-- Run in: Supabase Dashboard → SQL Editor
--
-- encounters.started_at is a timestamptz storing a real UTC instant
-- (Vetspire's start/startedAt fields come back with an explicit "Z" --
-- confirmed via vetspire_clinical_schema_probe.py, e.g.
-- "2026-08-30T21:22:36Z"), which Postgres stores correctly. But
-- `extract(dow/hour from started_at)` and `date(started_at)` read that
-- instant in whatever timezone the current session defaults to --
-- Supabase's default is UTC, not Chicago. A 4:22pm Central visit
-- (21:22 UTC) was showing up as hour 21 (9pm) instead of hour 16 (4pm),
-- and a visit after ~7pm Central could roll into the next UTC calendar
-- day for visit_date.
--
-- Fix: convert to America/Chicago before extracting anything. This
-- correctly handles the CDT/CST switch (America/Chicago, not a fixed
-- UTC-6 offset) automatically.
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                                            as encounter_id,
  e.started_at,
  extract(dow  from e.started_at at time zone 'America/Chicago')::int as day_of_week,   -- 0=Sunday .. 6=Saturday, Chicago local
  extract(hour from e.started_at at time zone 'America/Chicago')::int as hour_of_day,   -- Chicago local hour
  e.estimated_case_value                                          as case_value
from public.encounters e
where e.had_exam
  and e.started_at is not null;

create or replace view public.v_case_geo as
select
  e.location_id,
  c.postal_code,
  c.city,
  c.state,
  e.chief_complaint,
  date(e.started_at at time zone 'America/Chicago')               as visit_date
from public.encounters e
join public.clients c on c.id = e.client_id
where e.had_exam
  and e.started_at is not null
  and c.postal_code is not null;
