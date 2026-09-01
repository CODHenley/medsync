-- Wheaton's Location.openDate comes back null from Vetspire (same as Old
-- Orchard and West Loop), so the dashboard's Days Closed report fell back
-- to the earliest scheduled shift or billed day it could find as a proxy
-- for "opened" -- which for Wheaton landed on May 11, 2026, a handful of
-- pre-opening setup shifts/appointments that predate the location
-- actually seeing patients (confirmed against the practice's real
-- opening date: May 19, 2026).
--
-- Setting open_date directly here overrides that fallback -- the
-- dashboard already prefers locations.open_date over the proxy whenever
-- it's set (see loadClosedDaysReport in scoutsync_dashboard.html) -- so
-- Wheaton's tracked window floors at the right date instead of counting
-- those pre-opening days for or against it.

update public.locations
set open_date = '2026-05-19'
where id = '11111111-0000-0000-0000-000000000004';
