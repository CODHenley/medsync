-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Referral/rDVM marketing analytics (stage 1 of 2)
-- Run in: Supabase Dashboard → SQL Editor
--
-- Backs the new Marketing tab's three sections. Stage 2 (rDVM
-- visit-logging synced to/from Vetspire's own RdvmVisit feature) is
-- separate future work -- nothing here builds toward that.
--
--   1. Case Volume by Referring Vet -- v_referral_case_volume, built
--      entirely from data already synced (encounters + referral_relationships,
--      no new Vetspire fields needed). Only referral_type = 'rdvm_primary_care'
--      counts as a real referral source here -- the competitor types
--      already feed a different signal (v_competitor_use_signal in
--      scoutsync_clinical_financial_schema.sql) and aren't conflated with
--      this ranking.
--   2. Revenue by Referring Hospital -- rdvm_revenue_daily, populated by a
--      new salesReport breakdown (RDVM_ID) added to
--      vetspire_financial_sync.py. Same "never NULL, sentinel-default the
--      dimension id" convention as product_category_id/revenue_center_id
--      (scoutsync_revenue_centers.sql) -- Postgres never matches NULL to
--      NULL in ON CONFLICT, so a rDVM-less row would insert a fresh
--      duplicate every run instead of updating one. vetspire_rdvm_id is
--      text here (unlike the other two, which are integer columns), so its
--      sentinel is the string '0', not the integer 0.
--   3. Referral Origin Map -- reuses referral_relationships, extended with
--      the rDVM's own postal_code/city/state (confirmed live via GraphQL
--      introspection: Rdvm.postalCode et al. are real, populated top-level
--      fields -- 20/20 sampled rDVMs had one). Synced by
--      vetspire_clinical_sync.py alongside the fields it already pulls from
--      the nested rdvm{} block on clientRdvms. Reuses the existing
--      ZIP_CENTROIDS/Leaflet approach from the Chicagoland case map --
--      no new geocoding dependency, no new lat/lng storage.
--
-- IMPORTANT judgment call -- vetspire_referral_id (already on this table)
-- turns out to be Vetspire's ClientRdvm.id (the per-client relationship
-- join record), NOT the Rdvm entity's own id -- confirmed by reading
-- vetspire_clinical_sync.py's own query: `referrals` is keyed by `cr["id"]`
-- (the clientRdvms edge), while `rdvm.get("id")` is never itself captured
-- anywhere. salesReport's RDVM_ID breakdown returns the real Rdvm.id, which
-- would NOT match vetspire_referral_id. A new vetspire_rdvm_id column below
-- captures the real Rdvm.id separately so revenue rows can join back to a
-- referral_relationships row correctly instead of silently mismatching on
-- the wrong id.
-- ══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- Section 3 data: rDVM identity + address, synced straight from
-- Vetspire's Rdvm{} block (no geocoding -- ZIP-centroid lookup only, same
-- table ZIP_CENTROIDS already used by the Chicagoland case map).
-- ─────────────────────────────────────────────────────────────
alter table public.referral_relationships
  add column if not exists vetspire_rdvm_id text,
  add column if not exists city             text,
  add column if not exists state            text,
  add column if not exists postal_code      text;

comment on column public.referral_relationships.vetspire_rdvm_id is
  'The real Vetspire Rdvm.id (the hospital/vet entity itself) -- distinct '
  'from vetspire_referral_id on this same table, which is Vetspire '
  'ClientRdvm.id (a per-client relationship record). salesReport''s '
  'RDVM_ID breakdown (rdvm_revenue_daily) returns Rdvm.id, so a join '
  'against real revenue must use this column, not vetspire_referral_id.';

comment on column public.referral_relationships.postal_code is
  'From Vetspire Rdvm.postalCode (confirmed live: 20/20 sampled rDVMs had '
  'one) -- feeds the Referral Origin Map''s ZIP-centroid grouping, same '
  'approach as clients.postal_code on the Chicagoland case map '
  '(scoutsync_case_maps_and_heatmaps.sql). No street-level address kept, '
  'matching this schema''s existing no-full-PII convention.';

create index if not exists idx_referral_relationships_rdvm_id on public.referral_relationships(vetspire_rdvm_id);
create index if not exists idx_referral_relationships_postal_code on public.referral_relationships(postal_code);


-- ─────────────────────────────────────────────────────────────
-- Section 1: case volume by referring vet -- no new sync needed, both
-- source tables are already populated.
-- ─────────────────────────────────────────────────────────────
-- Pre-aggregated to one row per day (like v_financial_kpis_daily), not
-- collapsed across all history -- the Marketing tab needs to filter this by
-- the page's selected date range the same way every other section does,
-- which a single all-time count per rDVM couldn't support. The query layer
-- sums case_count across days (and across vetspire_referral_id rows that
-- share a referral_name, the same way it already merges same-name
-- providers on Revenue per Veterinarian) for whatever range is selected.
create or replace view public.v_referral_case_volume as
select
  e.location_id,
  date(e.started_at)   as case_date,
  rr.vetspire_referral_id,
  rr.referral_name,
  rr.referral_type,
  count(*) as case_count
from public.encounters e
join public.clients c                 on c.id = e.client_id
join public.referral_relationships rr on rr.client_id = c.id
where e.had_exam
  and e.started_at is not null
  and rr.referral_type = 'rdvm_primary_care'
group by e.location_id, date(e.started_at), rr.vetspire_referral_id, rr.referral_name, rr.referral_type;


-- ─────────────────────────────────────────────────────────────
-- Section 2: revenue by referring hospital -- needs the new
-- vetspire_financial_sync.py RDVM_ID breakdown sync (see that file's
-- SYNC_RDVM_REVENUE gate) to actually populate. Table exists as soon as
-- this migration runs; it's simply empty until a human dispatches
-- vetspire_rdvm_revenue_sync.yml at least once.
-- ─────────────────────────────────────────────────────────────
create table if not exists public.rdvm_revenue_daily (
  id               uuid primary key default gen_random_uuid(),
  location_id      uuid references public.locations(id) on delete set null,
  vetspire_rdvm_id text not null default '0',
  service_date     date not null,
  amount           numeric(10,2) not null,
  created_at       timestamptz default now()
);

create unique index if not exists idx_rdvm_revenue_daily_natural_key
  on public.rdvm_revenue_daily(location_id, vetspire_rdvm_id, service_date);

create index if not exists idx_rdvm_revenue_daily_location_date
  on public.rdvm_revenue_daily(location_id, service_date);

alter table public.rdvm_revenue_daily enable row level security;
drop policy if exists "anon_all" on public.rdvm_revenue_daily;
create policy "anon_all" on public.rdvm_revenue_daily for all to anon using (true) with check (true);
