-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Per-ZIP demographic/economic profile (U.S. Census ACS)
-- Run in: Supabase Dashboard → SQL Editor
--
-- Feeds the de novo location-ramp-up projection: each hospital's service
-- area (its real client ZIP mix, from v_case_geo) gets weighted by these
-- figures so a new location is benchmarked against mature locations with
-- a genuinely similar area, not a flat average of all of them. "Pet
-- ownership by ZIP" isn't published free/public data, so this uses ACS's
-- standard economic/demographic variables as the available proxy:
--   median_household_income  -- B19013_001E, past-12-months $, ACS 5-year
--   population                -- B01003_001E, total population, ZCTA
--   median_age                -- B01002_001E
--   avg_household_size        -- B25010_001E, average size of occupied housing units
-- Populated by census_zip_demographics_sync.py (workflow_dispatch +
-- scheduled refresh, since ACS updates ~annually).
-- ══════════════════════════════════════════════════════════════

create table if not exists public.zip_demographics (
  zip_code                 text primary key,
  median_household_income  numeric,
  population                integer,
  median_age                numeric,
  avg_household_size        numeric,
  acs_vintage               text,           -- e.g. '2022' -- the ACS 5-year end year this came from
  synced_at                 timestamptz default now()
);

alter table public.zip_demographics enable row level security;
drop policy if exists "anon_all" on public.zip_demographics;
create policy "anon_all" on public.zip_demographics for all to anon using (true) with check (true);
