-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Clinical Operations & Financial schema
-- Run in: Supabase Dashboard → SQL Editor
--
-- Adds the tables ScoutSync needs beyond what MedSync already has
-- (Facilities Operations / Inventory & Procurement is already fully
-- covered by lots, po_items, purchase_history, goods_lost,
-- inventory_snapshots, dispensed_items — no new tables there).
--
-- Column names on the Vetspire-sourced tables are MedSync's own
-- internal names, not Vetspire's GraphQL field names — those are
-- still being confirmed via vetspire_clinical_schema_probe.py.
-- Sync jobs map Vetspire's actual fields into this shape.
-- ══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- CLINICAL OPERATIONS
-- ─────────────────────────────────────────────────────────────

-- Vetspire provider/staff roster, bridged to MedSync locations.
-- Backs revenue-per-vet, visits-per-provider, and (joined with Rippling
-- once that sync exists) staff-cost-percentage KPIs.
create table if not exists public.providers (
  id                  uuid primary key default gen_random_uuid(),
  vetspire_provider_id text not null unique,
  full_name           text not null,
  provider_type       text not null default 'dvm'
                        check (provider_type in ('dvm', 'tech', 'other')),
  location_id         uuid references public.locations(id) on delete set null,
  is_active           boolean default true,
  created_at          timestamptz default now()
);

-- Minimal client bridge — deliberately lean, no full PII duplication.
-- Only what the referral/competitor-use KPI and new-vs-established
-- client counting need.
create table if not exists public.clients (
  id                  uuid primary key default gen_random_uuid(),
  vetspire_client_id  text not null unique,
  location_id         uuid references public.locations(id) on delete set null,
  first_encounter_at  timestamptz,
  created_at          timestamptz default now()
);

create table if not exists public.patients (
  id                  uuid primary key default gen_random_uuid(),
  vetspire_patient_id text not null unique,
  client_id           uuid references public.clients(id) on delete cascade,
  species             text,
  created_at          timestamptz default now()
);

-- Core clinical fact table. `started_at` is the Vetspire encounter-start
-- ("arrived") button press — the canonical "a visit happened" timestamp,
-- not the scheduled appointment time.
create table if not exists public.encounters (
  id                    uuid primary key default gen_random_uuid(),
  vetspire_encounter_id text not null unique,
  location_id           uuid references public.locations(id) on delete set null,
  client_id             uuid references public.clients(id) on delete set null,
  patient_id            uuid references public.patients(id) on delete set null,
  provider_id           uuid references public.providers(id) on delete set null,
  visit_type            text,               -- e.g. urgent_care, recheck, surgery
  is_new_client         boolean default false,
  checked_in_at         timestamptz,         -- scheduled/check-in time, if distinct
  started_at            timestamptz,         -- encounter-start ("arrived") — canonical event
  completed_at          timestamptz,
  chief_complaint       text,
  created_at            timestamptz default now()
);

-- rDVM / referral relationships Vetspire already tracks for marketing
-- purposes. `referral_type` distinguishes a true rDVM (feeds patients TO
-- Scout) from a competing urgent care (client also USES a competitor) —
-- only the latter feeds the competitor-use KPI.
create table if not exists public.referral_relationships (
  id                  uuid primary key default gen_random_uuid(),
  vetspire_referral_id text unique,
  client_id           uuid references public.clients(id) on delete cascade,
  referral_name       text not null,
  referral_type       text not null default 'other'
                        check (referral_type in (
                          'rdvm_primary_care', 'competitor_urgent_care',
                          'competitor_er', 'other'
                        )),
  listed_at           timestamptz,
  created_at          timestamptz default now()
);

-- Records-release events logged in Vetspire. Cross-referenced against
-- referral_relationships where referral_type = 'competitor_urgent_care'
-- (or 'competitor_er') to detect concurrent competitor use.
create table if not exists public.records_release_log (
  id                      uuid primary key default gen_random_uuid(),
  vetspire_release_id     text unique,
  client_id               uuid references public.clients(id) on delete cascade,
  referral_relationship_id uuid references public.referral_relationships(id) on delete set null,
  released_at             timestamptz not null,
  method                   text,             -- e.g. email, fax, portal
  created_at               timestamptz default now()
);


-- ─────────────────────────────────────────────────────────────
-- FINANCIAL
-- ─────────────────────────────────────────────────────────────

-- Line-item detail from Vetspire's salesReport (currently collapsed to a
-- single daily sum in daily_revenue — this table keeps the row-level
-- provider + category breakdown salesReport already returns).
-- Backs ATC, Revenue by Source, and Revenue per Veterinarian.
create table if not exists public.invoice_line_items (
  id              uuid primary key default gen_random_uuid(),
  vetspire_invoice_id text,
  encounter_id    uuid references public.encounters(id) on delete set null,
  location_id     uuid references public.locations(id) on delete set null,
  provider_id     uuid references public.providers(id) on delete set null,
  category        text not null default 'other'
                    check (category in (
                      'professional_services', 'diagnostics', 'retail_pharmacy', 'other'
                    )),
  description     text,
  amount          numeric(10,2) not null,
  service_date    date not null,
  created_at      timestamptz default now()
);


-- ─────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────
create index if not exists idx_encounters_location_started   on public.encounters(location_id, started_at);
create index if not exists idx_encounters_client              on public.encounters(client_id);
create index if not exists idx_encounters_provider             on public.encounters(provider_id);
create index if not exists idx_referral_relationships_client   on public.referral_relationships(client_id);
create index if not exists idx_referral_relationships_type     on public.referral_relationships(referral_type);
create index if not exists idx_records_release_client          on public.records_release_log(client_id);
create index if not exists idx_records_release_referral        on public.records_release_log(referral_relationship_id);
create index if not exists idx_invoice_line_items_location_date on public.invoice_line_items(location_id, service_date);
create index if not exists idx_invoice_line_items_provider      on public.invoice_line_items(provider_id);
create index if not exists idx_invoice_line_items_category      on public.invoice_line_items(category);


-- ─────────────────────────────────────────────────────────────
-- RLS — anon read/write, matching existing MedSync convention
-- ─────────────────────────────────────────────────────────────
do $$
declare
  t text;
  tables text[] := array[
    'providers', 'clients', 'patients', 'encounters',
    'referral_relationships', 'records_release_log', 'invoice_line_items'
  ];
begin
  foreach t in array tables loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "anon_all" on public.%I', t);
    execute format(
      'create policy "anon_all" on public.%I for all to anon using (true) with check (true)', t
    );
  end loop;
end $$;


-- ─────────────────────────────────────────────────────────────
-- Views — Clinical KPIs
-- ─────────────────────────────────────────────────────────────

-- Visits/day, new-vs-established client mix, avg encounter duration, per location+provider
create or replace view public.v_clinical_kpis_daily as
select
  e.location_id,
  e.provider_id,
  date(e.started_at)                                            as visit_date,
  count(*)                                                        as encounter_count,
  count(*) filter (where e.is_new_client)                         as new_client_count,
  avg(extract(epoch from (e.completed_at - e.started_at)) / 60)   as avg_encounter_minutes,
  avg(extract(epoch from (e.started_at - e.checked_in_at)) / 60)  as avg_wait_minutes
from public.encounters e
where e.started_at is not null
group by e.location_id, e.provider_id, date(e.started_at);

-- Competitor-use signal: clients with a competitor referral listed AND a
-- records-release event to that same referral within the trailing window.
create or replace view public.v_competitor_use_signal as
select
  rr.client_id,
  rr.referral_name,
  rr.referral_type,
  rl.released_at,
  c.location_id
from public.referral_relationships rr
join public.records_release_log rl
  on rl.referral_relationship_id = rr.id
join public.clients c
  on c.id = rr.client_id
where rr.referral_type in ('competitor_urgent_care', 'competitor_er');


-- ─────────────────────────────────────────────────────────────
-- Views — Financial KPIs
-- ─────────────────────────────────────────────────────────────

-- Average Transaction Charge, Revenue by Source, per location+date
create or replace view public.v_financial_kpis_daily as
select
  location_id,
  service_date,
  category,
  sum(amount)                          as revenue,
  count(distinct vetspire_invoice_id)  as invoice_count,
  sum(amount) / nullif(count(distinct vetspire_invoice_id), 0) as avg_transaction_charge
from public.invoice_line_items
group by location_id, service_date, category;

-- Revenue per Veterinarian (rolling — filter by date range in the query layer)
create or replace view public.v_revenue_per_provider as
select
  provider_id,
  location_id,
  sum(amount) as total_revenue
from public.invoice_line_items
where provider_id is not null
group by provider_id, location_id;
