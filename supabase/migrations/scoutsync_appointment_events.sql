-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Appointment events (cancellations, deletions, no-shows), for
-- a standalone Cancellations & Deletions operations report and a
-- cancellation-rate-based "partial closure" flag on the Days Closed report.
--
-- Confirmed live against production (vetspire_cancellations_blockoff_probe.py)
-- that Vetspire's appointments(includeDeleted: true) query returns real
-- deleted/status data (deletedBy, deletionReason, status incl. CANCELLED/
-- NOSHOW) -- and separately, that AppointmentType.isBlockoff is NOT a
-- closure signal (93% of one location's appointments in a 60-day window
-- were blockoffs, almost all routine "Lunch"/"Booking Appointment" slots
-- capped at 60 minutes) -- so blockoff-typed rows are excluded at sync time,
-- not stored here.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.appointment_events (
  id                        uuid primary key default gen_random_uuid(),
  vetspire_appointment_id   text not null unique,
  location_id               uuid not null references public.locations(id),
  provider_id               uuid references public.providers(id),
  appointment_type          text,
  scheduled_start           timestamptz,
  status                    text,
  deleted                   boolean not null default false,
  deleted_by_provider_id    uuid references public.providers(id),
  deletion_reason           text,
  duration_minutes          int,
  inserted_at               timestamptz not null default now()
);

create index if not exists idx_appointment_events_location_date
  on public.appointment_events (location_id, scheduled_start);
create index if not exists idx_appointment_events_provider_date
  on public.appointment_events (provider_id, scheduled_start);
create index if not exists idx_appointment_events_status
  on public.appointment_events (status);

comment on table public.appointment_events is
  'Vetspire appointments (any status, blockoff-typed rows excluded) -- backs the Cancellations & Deletions operations report and the "high cancellation rate" partial-closure flag on the Days Closed report. status/deleted/deletedBy/deletionReason come straight from Vetspire, no inference.';

alter table public.appointment_events enable row level security;
drop policy if exists "anon_all" on public.appointment_events;
create policy "anon_all" on public.appointment_events for all to anon using (true) with check (true);
