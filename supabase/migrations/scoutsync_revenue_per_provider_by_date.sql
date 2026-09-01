-- v_revenue_per_provider's own comment said "filter by date range in the
-- query layer" but the view had no date column to filter on -- so the
-- Revenue per Veterinarian chart on the dashboard has always shown
-- all-time totals per provider, regardless of the date range selected at
-- the top of the page. Add service_date so the query layer can actually
-- do what the original comment assumed.

-- service_date is appended AFTER total_revenue, not inserted before it --
-- CREATE OR REPLACE VIEW requires existing output columns to keep the same
-- name/position; a new column can only be added at the end of the list.
-- (The first version of this migration put service_date 3rd, ahead of
-- total_revenue, which silently failed with "cannot change name of view
-- column \"total_revenue\" to \"service_date\"" and left the view
-- unchanged -- so the dashboard's service_date filter hit a nonexistent
-- column and the Revenue per Veterinarian chart rendered empty.)
create or replace view public.v_revenue_per_provider as
select
  provider_id,
  location_id,
  sum(amount) as total_revenue,
  service_date
from public.invoice_line_items
where provider_id is not null
group by provider_id, location_id, service_date;
