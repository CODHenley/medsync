-- v_revenue_per_provider's own comment said "filter by date range in the
-- query layer" but the view had no date column to filter on -- so the
-- Revenue per Veterinarian chart on the dashboard has always shown
-- all-time totals per provider, regardless of the date range selected at
-- the top of the page. Add service_date so the query layer can actually
-- do what the original comment assumed.

create or replace view public.v_revenue_per_provider as
select
  provider_id,
  location_id,
  service_date,
  sum(amount) as total_revenue
from public.invoice_line_items
where provider_id is not null
group by provider_id, location_id, service_date;
