-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Provider shift schedules, for distinguishing "staffed but no
-- revenue" from "actually closed" in the Days Closed & Financial Impact
-- report.
--
-- Neither encounters nor billed revenue can make that distinction -- both
-- only reflect patient-visit activity, not staff presence. Vetspire's
-- Location.providerSchedules(startDate, endDate) returns one row per
-- provider per scheduled shift-day, independent of whether any encounter
-- or invoice happened that day -- confirmed live against production via
-- vetspire_scheduling_schema_probe.py / vetspire_location_root_query_probe.py.
-- vetspire_provider_shifts_sync.py populates this table from that field.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.provider_shifts (
  id                 uuid primary key default gen_random_uuid(),
  vetspire_shift_id  text not null unique,
  location_id        uuid not null references public.locations(id),
  provider_id        uuid references public.providers(id),
  shift_start        date not null,
  shift_end          date not null,
  inserted_at        timestamptz not null default now()
);

create index if not exists idx_provider_shifts_location_dates
  on public.provider_shifts (location_id, shift_start, shift_end);

comment on table public.provider_shifts is
  'Vetspire Location.providerSchedules -- one row per provider per scheduled shift-day, independent of billed revenue or encounters. Used to tell "staffed but slow" apart from "actually closed."';

-- Every other sync table (e.g. encounter_diagnostics) follows this same
-- pattern -- a bare new table has no RLS policy and the anon key the sync
-- scripts run under gets rejected with 42501 on the first insert.
alter table public.provider_shifts enable row level security;
drop policy if exists "anon_all" on public.provider_shifts;
create policy "anon_all" on public.provider_shifts for all to anon using (true) with check (true);

-- Discovered live (PGRST204) that locations.open_date doesn't actually
-- exist in this project -- a different tool's payload-building code
-- (medsync_newlocation_live.html) conditionally sets it, which had wrongly
-- suggested the column was already there. vetspire_provider_shifts_sync.py
-- needs it to backfill each location's real Vetspire-reported opening date.
alter table public.locations add column if not exists open_date date;
