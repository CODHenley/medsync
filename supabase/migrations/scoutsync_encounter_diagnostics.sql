-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Clinical: diagnostics (tests/procedures) ordered per encounter
-- Run in: Supabase Dashboard → SQL Editor
--
-- Vetspire's Diagnostic type is diagnostic TESTS/PROCEDURES ordered
-- (e.g. "Ultrasound - POCUS", "Fluorescein Corneal Stain") — confirmed via
-- vetspire_clinical_schema_probe.py — not a clinical diagnosis/condition.
-- Backs the day drill-down panel's "top diagnostics" list and per-provider
-- diagnostics count on the ScoutSync Executive Dashboard.
--
-- provider_id is nullable (no sentinel needed, unlike invoice_line_items) —
-- the natural key here is vetspire_diagnostic_id alone, so a null
-- provider_id never collides on ON CONFLICT the way a composite key would.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.encounter_diagnostics (
  id                      uuid primary key default gen_random_uuid(),
  vetspire_diagnostic_id  text unique,
  encounter_id            uuid references public.encounters(id) on delete cascade,
  location_id             uuid references public.locations(id) on delete set null,
  provider_id             uuid references public.providers(id) on delete set null,
  name                    text not null,
  service_date            date not null,
  created_at              timestamptz default now()
);

create index if not exists idx_encounter_diagnostics_date     on public.encounter_diagnostics(service_date);
create index if not exists idx_encounter_diagnostics_provider on public.encounter_diagnostics(provider_id);
create index if not exists idx_encounter_diagnostics_location on public.encounter_diagnostics(location_id);

alter table public.encounter_diagnostics enable row level security;
drop policy if exists "anon_all" on public.encounter_diagnostics;
create policy "anon_all" on public.encounter_diagnostics for all to anon using (true) with check (true);
