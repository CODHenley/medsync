-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Standalone rDVM directory (fix for Marketing tab names)
-- Run in: Supabase Dashboard → SQL Editor
--
-- Bug: the Marketing tab's Revenue by Referring Hospital section showed
-- "rDVM <id>" instead of a real name for most rows, and the Referral Origin
-- Map showed no postal codes at all. Root cause: referral_relationships
-- (scoutsync_referral_marketing_analytics.sql) only gets a row for an rDVM
-- linked to a client with a RECENT encounter -- vetspire_clinical_sync.py's
-- rolling LOOKBACK_DAYS window, default 3 days. rdvm_revenue_daily covers a
-- full year via salesReport and isn't tied to any client's encounter
-- recency at all, so most high-revenue rDVMs were never captured by that
-- narrower, encounter-triggered sync.
--
-- Fix: a complete, standalone directory of every Rdvm Vetspire has on file
-- (~1,126 records per rdvmsCount), synced independently of any client/
-- encounter/referral activity by vetspire_rdvm_directory_sync.py via the
-- rdvms(limit, offset) query (confirmed live: standard limit/offset
-- pagination). This becomes the authoritative name/address source for the
-- Marketing tab -- referral_relationships is still what ties a specific
-- client to a specific rDVM (needed for Case Volume by Referring Vet), but
-- name/address resolution no longer depends on that narrower table having
-- a matching row.
-- ══════════════════════════════════════════════════════════════

create table if not exists public.rdvm_directory (
  id                uuid primary key default gen_random_uuid(),
  vetspire_rdvm_id  text not null,
  name              text,
  is_active         boolean,
  city              text,
  state             text,
  postal_code       text,
  updated_at        timestamptz default now()
);

create unique index if not exists idx_rdvm_directory_vetspire_id
  on public.rdvm_directory(vetspire_rdvm_id);

create index if not exists idx_rdvm_directory_postal_code
  on public.rdvm_directory(postal_code);

alter table public.rdvm_directory enable row level security;
drop policy if exists "anon_all" on public.rdvm_directory;
create policy "anon_all" on public.rdvm_directory for all to anon using (true) with check (true);


-- v_referral_case_volume (scoutsync_referral_marketing_analytics.sql)
-- selected vetspire_referral_id (the ClientRdvm join id) but not
-- vetspire_rdvm_id (the real Rdvm id) -- the Referral Origin Map needs the
-- latter to join against rdvm_directory for a postal code, since
-- referral_relationships.postal_code is itself only populated for rows
-- touched by a sync run since that column was added (the same staleness
-- problem this whole migration exists to fix).
--
-- vetspire_rdvm_id is appended as the LAST selected column, after
-- case_count, not inserted alongside the other rr.* columns -- Postgres's
-- CREATE OR REPLACE VIEW only allows ADDING columns at the end of the
-- list; inserting one in the middle shifts every later column's ordinal
-- position, which Postgres treats as an attempt to RENAME that column
-- (blocked with error 42P16 -- confirmed live when this migration was
-- first attempted). Appending at the end is the only shape that's a pure
-- addition.
create or replace view public.v_referral_case_volume as
select
  e.location_id,
  date(e.started_at)   as case_date,
  rr.vetspire_referral_id,
  rr.referral_name,
  rr.referral_type,
  count(*) as case_count,
  rr.vetspire_rdvm_id
from public.encounters e
join public.clients c                 on c.id = e.client_id
join public.referral_relationships rr on rr.client_id = c.id
where e.had_exam
  and e.started_at is not null
  and rr.referral_type = 'rdvm_primary_care'
group by e.location_id, date(e.started_at), rr.vetspire_referral_id, rr.referral_name, rr.referral_type, rr.vetspire_rdvm_id;
