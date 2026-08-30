-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Case volume/value heatmaps + Chicagoland geo-illness map
-- Run in: Supabase Dashboard → SQL Editor
--
-- Adds what's needed for three new dashboard features:
--   1. Case volume heatmap (day-of-week x hour-of-day)
--   2. Case dollar-value heatmap (same grid)
--   3. Chicagoland map: hospital locations + patient-address density,
--      broken out by chief_complaint (Vetspire has no populated
--      diagnosis field at this practice -- confirmed via
--      vetspire_clinical_schema_probe.py: Problem, PatientDiagnosis,
--      and Diagnosis are all empty across a 180-day/20-patient sample.
--      chief_complaint is sourced from Appointment.reason, the actual
--      free-text reason-for-visit staff enter at booking -- confirmed
--      populated on 233/300 (78%) of a recent sample, e.g. "Vomiting",
--      "Eye Issues", "Skin issues". It's free text, not a coded
--      diagnosis, and is labeled as reason-for-visit everywhere it's
--      shown, never as "diagnosis").
--
-- "Case" = an encounter with had_exam = true -- REUSES the existing
-- encounters.had_exam column (scoutsync_exam_visit_flag.sql), not a new
-- definition. had_exam is Megan's already-shipped correction for
-- "Visits/Provider": any invoice line item (EncounterProduct) with
-- "Exam" in its name. This is the same concept the user asked for here
-- ("any encounter where an exam is performed") -- introducing a second,
-- competing "exam" signal (e.g. Vetspire's separate encounterType.name
-- enum, which also happens to have a literal 'Exam' value) would just
-- create two definitions of the same thing that can silently disagree.
--
-- Client address columns are deliberately lean (city/state/postal_code
-- only, no street line) -- matches this schema's existing no-full-PII
-- convention and is all a community/ZIP-level map needs.
-- ══════════════════════════════════════════════════════════════

alter table public.clients
  add column if not exists city text,
  add column if not exists state text,
  add column if not exists postal_code text;

comment on column public.clients.postal_code is
  'From Vetspire Client.addresses (isPrimary address if present, else '
  'the first one) -- confirmed sparse in practice (2/20 sampled clients '
  'had any address on file), so the geo map will only ever cover a '
  'subset of real case volume, not all of it.';

create index if not exists idx_clients_postal_code on public.clients(postal_code);


-- ─────────────────────────────────────────────────────────────
-- View: case volume + dollar value by day-of-week / hour-of-day
-- ─────────────────────────────────────────────────────────────
-- Dollar value joins invoice_line_items back through encounters (the
-- line items themselves only carry a date, not a time-of-day) --
-- confirmed via scoutsync_clinical_financial_schema.sql's own comment
-- that service_date is date-only.
create or replace view public.v_case_heatmap as
select
  e.location_id,
  e.id                                          as encounter_id,
  e.started_at,
  extract(dow from e.started_at)::int           as day_of_week,   -- 0=Sunday .. 6=Saturday
  extract(hour from e.started_at)::int          as hour_of_day,
  coalesce(sum(ili.amount), 0)                  as case_value
from public.encounters e
left join public.invoice_line_items ili on ili.encounter_id = e.id
where e.had_exam
  and e.started_at is not null
group by e.location_id, e.id, e.started_at;


-- ─────────────────────────────────────────────────────────────
-- View: geo case density by ZIP, with chief_complaint breakdown
-- ─────────────────────────────────────────────────────────────
create or replace view public.v_case_geo as
select
  e.location_id,
  c.postal_code,
  c.city,
  c.state,
  e.chief_complaint,
  date(e.started_at)                            as visit_date
from public.encounters e
join public.clients c on c.id = e.client_id
where e.had_exam
  and e.started_at is not null
  and c.postal_code is not null;
