-- Add min/max columns to products table
-- qty_min / qty_max are set by the Vetspire sync for tracked products
-- Products without these values (NULL) are not Vetspire-integrated and
-- will NOT appear in auto-recommended POs

ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS qty_min NUMERIC,
  ADD COLUMN IF NOT EXISTS qty_max NUMERIC;

-- Index for fast "has min/max" queries
CREATE INDEX IF NOT EXISTS products_has_minmax
  ON public.products (id)
  WHERE qty_min IS NOT NULL;
