-- ============================================================
-- dispensed_items_migration.sql
-- Lot lifecycle: captures what was sold/dispensed from Vetspire
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Dispensed items — one row per product line on a paid visit
CREATE TABLE IF NOT EXISTS public.dispensed_items (
  id                     UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  vetspire_product_id    TEXT NOT NULL,
  product_name           TEXT,
  sku                    TEXT,
  quantity               DECIMAL(10,4),
  quantity_remaining     DECIMAL(10,4),
  unit_price             DECIMAL(10,4),   -- what client was charged
  unit_cost              DECIMAL(10,4),   -- what we paid (from Vetspire product.unitCost)
  subtotal_cents         INTEGER,
  total_before_tax_cents INTEGER,
  returned               BOOLEAN DEFAULT false,
  refunded               BOOLEAN DEFAULT false,
  dispensed_at           TIMESTAMPTZ,     -- Vetspire orderItem.updatedAt
  location_id            TEXT,            -- Vetspire location ID (e.g. "28253")
  location_name          TEXT,            -- Human readable
  pulled_at              TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (vetspire_product_id, dispensed_at, location_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_dispensed_items_product   ON public.dispensed_items (vetspire_product_id);
CREATE INDEX IF NOT EXISTS idx_dispensed_items_location  ON public.dispensed_items (location_id);
CREATE INDEX IF NOT EXISTS idx_dispensed_items_date      ON public.dispensed_items (dispensed_at);
CREATE INDEX IF NOT EXISTS idx_dispensed_items_returned  ON public.dispensed_items (returned, refunded);

-- 2. View: product-level COGS summary
--    Joins dispensed_items with lots (purchase side) by product name for true lot lifecycle
CREATE OR REPLACE VIEW public.procurement_cogs_summary AS
SELECT
  di.vetspire_product_id,
  di.product_name,
  di.location_id,
  di.location_name,
  COUNT(*)                                          AS dispense_events,
  SUM(di.quantity)                                  AS total_qty_dispensed,
  SUM(CASE WHEN di.returned OR di.refunded THEN di.quantity ELSE 0 END) AS qty_returned,
  SUM(di.quantity * COALESCE(di.unit_cost, 0))      AS true_cogs,
  SUM(di.quantity * COALESCE(di.unit_price, 0))     AS total_revenue,
  MAX(di.dispensed_at)                              AS last_dispensed_at,
  MIN(di.dispensed_at)                              AS first_dispensed_at
FROM public.dispensed_items di
WHERE NOT (di.returned OR di.refunded)
GROUP BY di.vetspire_product_id, di.product_name, di.location_id, di.location_name;

-- 3. View: daily COGS roll-up by location
CREATE OR REPLACE VIEW public.procurement_daily_cogs AS
SELECT
  DATE(di.dispensed_at)                             AS dispense_date,
  di.location_id,
  di.location_name,
  COUNT(DISTINCT di.vetspire_product_id)            AS unique_products,
  SUM(di.quantity)                                  AS total_qty,
  SUM(di.quantity * COALESCE(di.unit_cost, 0))      AS true_cogs,
  SUM(di.quantity * COALESCE(di.unit_price, 0))     AS total_revenue
FROM public.dispensed_items di
WHERE NOT (di.returned OR di.refunded)
GROUP BY DATE(di.dispensed_at), di.location_id, di.location_name
ORDER BY dispense_date DESC;
