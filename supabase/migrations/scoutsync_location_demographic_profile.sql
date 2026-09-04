-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Per-location service-area demographic/economic profile
-- Run in: Supabase Dashboard → SQL Editor
--
-- Case-weighted average of zip_demographics across each location's real
-- client ZIP mix (v_case_geo -- one row per case, already the same "case"
-- definition as the heatmaps/seasonal chart). Feeds the de novo ramp-up
-- projection: a new location gets benchmarked against mature locations
-- with a genuinely similar service area, not a flat average of all of
-- them. Returns nulls for a location until zip_demographics has been
-- populated (see census_zip_demographics_sync.py) -- the ramp-up chart
-- falls back to an unweighted average across mature locations until then.
-- ══════════════════════════════════════════════════════════════

create or replace view public.v_location_zip_counts as
select location_id, postal_code, count(*) as case_count
from public.v_case_geo
group by location_id, postal_code;

create or replace view public.v_location_demographic_profile as
select
  lzc.location_id,
  sum(lzc.case_count) as total_cases,
  sum(lzc.case_count) filter (where zd.median_household_income is not null) as income_weight,
  sum(lzc.case_count * zd.median_household_income)
    / nullif(sum(lzc.case_count) filter (where zd.median_household_income is not null), 0) as avg_median_household_income,
  sum(lzc.case_count * zd.population)
    / nullif(sum(lzc.case_count) filter (where zd.population is not null), 0) as avg_population,
  sum(lzc.case_count * zd.median_age)
    / nullif(sum(lzc.case_count) filter (where zd.median_age is not null), 0) as avg_median_age,
  sum(lzc.case_count * zd.avg_household_size)
    / nullif(sum(lzc.case_count) filter (where zd.avg_household_size is not null), 0) as avg_household_size
from public.v_location_zip_counts lzc
left join public.zip_demographics zd on zd.zip_code = lzc.postal_code
group by lzc.location_id;
