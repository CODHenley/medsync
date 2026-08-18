-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Clinical: exam-based visit flag for Visits/Provider
-- Run in: Supabase Dashboard → SQL Editor
--
-- Megan's correction: "Visits / Provider" should only count visits where
-- an exam was actually performed — any invoice line item (Vetspire
-- EncounterProduct) with "Exam" in its name — not every encounter row.
-- This excludes med refills, drop-offs, and other non-exam services from
-- that specific metric. Total Visits is unaffected — it still counts every
-- encounter, since that tile measures overall visit volume, not exams.
-- ══════════════════════════════════════════════════════════════

alter table public.encounters add column if not exists had_exam boolean not null default false;

create index if not exists idx_encounters_had_exam on public.encounters(had_exam);

-- CREATE OR REPLACE only allows appending new columns at the END of the
-- select list — inserting one in the middle shifts every column after it,
-- which Postgres treats as a rename and rejects (42P16). exam_visit_count
-- goes last, after every pre-existing column.
create or replace view public.v_clinical_kpis_daily as
select
  e.location_id,
  e.provider_id,
  date(e.started_at)                                            as visit_date,
  count(*)                                                        as encounter_count,
  count(*) filter (where e.is_new_client)                         as new_client_count,
  avg(extract(epoch from (e.completed_at - e.started_at)) / 60)   as avg_encounter_minutes,
  avg(extract(epoch from (e.started_at - e.checked_in_at)) / 60)  as avg_wait_minutes,
  count(*) filter (where e.had_exam)                              as exam_visit_count
from public.encounters e
where e.started_at is not null
group by e.location_id, e.provider_id, date(e.started_at);
