-- ============================================================
-- Add order_item_id to dispensed_items
-- Run in Supabase SQL Editor
-- ============================================================

-- 1. Truncate existing data (incorrect due to timestamp deduplication)
TRUNCATE TABLE public.dispensed_items;

-- 2. Add order_item_id column
ALTER TABLE public.dispensed_items
  ADD COLUMN IF NOT EXISTS order_item_id TEXT;

-- 3. Drop old unique constraint
ALTER TABLE public.dispensed_items
  DROP CONSTRAINT IF EXISTS dispensed_items_vetspire_product_id_dispensed_at_location_id_key;

-- 4. New unique constraint: order_item_id per location (when present)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dispensed_items_order_item_loc
  ON public.dispensed_items (order_item_id, location_id)
  WHERE order_item_id IS NOT NULL;

-- 5. Fallback unique constraint for rows without order_item_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_dispensed_items_legacy_key
  ON public.dispensed_items (vetspire_product_id, dispensed_at, location_id)
  WHERE order_item_id IS NULL;
