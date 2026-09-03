-- Adds patient identity to appointment_events, needed to tell a real
-- cancellation/deletion apart from a same-day reschedule (the same patient
-- rebooked later that day at the same location) -- appointment_events had
-- no way to know which appointments belonged to the same patient until now.
--
-- Stored as Vetspire's own patient id (text, matching the pattern already
-- used for vetspire_appointment_id/vetspire_provider_id elsewhere in this
-- table) rather than a foreign key into a patients table, since this repo
-- doesn't sync a patients table at all -- the id is only ever used to group
-- same-patient appointments together, never displayed or joined elsewhere.

alter table public.appointment_events
  add column if not exists vetspire_patient_id text;

create index if not exists idx_appointment_events_patient_date
  on public.appointment_events (vetspire_patient_id, location_id, scheduled_start);
