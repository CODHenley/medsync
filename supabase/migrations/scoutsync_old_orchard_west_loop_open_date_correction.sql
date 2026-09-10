-- Old Orchard and West Loop's Location.openDate comes back null from
-- Vetspire (same gap already fixed once for Wheaton -- see
-- scoutsync_wheaton_open_date_correction.sql). Setting open_date directly
-- here uses the dates already shown in the Days Closed & Financial Impact
-- report's "Opened" column for these two locations (that report's own
-- fallback: earliest scheduled shift or billed day on file, since Vetspire
-- doesn't supply a real one) -- the dashboard already prefers
-- locations.open_date over that fallback whenever it's set, so this just
-- makes it authoritative instead of recomputed per page load.

update public.locations
set open_date = '2024-12-26'
where id = '11111111-0000-0000-0000-000000000002'; -- Old Orchard

update public.locations
set open_date = '2024-08-27'
where id = '11111111-0000-0000-0000-000000000003'; -- West Loop
