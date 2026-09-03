-- ══════════════════════════════════════════════════════════════
-- ScoutSync — Add product category to dispensed_items
-- Run in: Supabase Dashboard → SQL Editor
--
-- Needed for: clicking a category bar in Revenue by Source to drill down
-- into the individual services/products that make up it, with a count of
-- how many times each occurred. invoice_line_items (Revenue by Source's own
-- source) has no per-service name at all -- it's Vetspire salesReport's
-- pre-aggregated location+provider+category+day totals. dispensed_items
-- (fed by usageReport.orderItems, used today for inventory/COGS) already
-- has one row per real billed order item with a product name -- confirmed
-- via scoutsync_service_category_probe.py that its dollar total covers
-- 100.3% of salesReport revenue for the same window/location, i.e. it's a
-- reliable stand-in for "every billed line item," not just inventory-
-- tracked pharmacy products.
--
-- Also confirmed live via that probe: Product.productCategories is a real,
-- populated field (previously never queried) that returns a LIST -- most
-- products carry zero or one category in practice, none seen with more
-- than one, but the sync stores only the first if several are ever
-- present (documented at the call site). Its id space was confirmed to
-- fully match product_categories (588/588 sampled rows matched, 0
-- mismatches) -- the same 18-category reference table Revenue by Source
-- already uses, synced separately via `productCategories { id name }` in
-- vetspire_financial_sync.py. A little under 60% of sampled order items
-- had no category at all (Vetspire's own gap, same shape as invoice_line_
-- items' "Category 0"/Uncategorized bucket) -- the drill-down needs an
-- Uncategorized bucket of its own, not a hard requirement that every
-- product have one.
--
-- No FK to product_categories(id) -- invoice_line_items.product_category_id
-- doesn't have one either, for the same reason: product_categories is
-- refreshed periodically by a different sync, so a brand-new category
-- could plausibly show up here before that table catches up. A hard FK
-- would turn that ordering gap into an insert failure on the live 5-minute
-- intraday sync.
-- ══════════════════════════════════════════════════════════════

alter table public.dispensed_items
  add column if not exists product_category_id integer;

create index if not exists idx_dispensed_items_category
  on public.dispensed_items (product_category_id, location_id, dispensed_at);

comment on column public.dispensed_items.product_category_id is
  'Vetspire Product.productCategories[0].id (first category if a product '
  'ever carries more than one) -- null when Vetspire has no category on '
  'file for that product. Same id space as product_categories.id.';
