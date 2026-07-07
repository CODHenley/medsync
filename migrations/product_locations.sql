-- product_locations: tracks which products are enabled at each Scout location.
-- Populated and maintained by products_sync.py (daily 7:30am CT).
-- A product absent from a location's VetSpire list is set enabled=false
-- on the next sync run — no manual intervention required.

CREATE TABLE IF NOT EXISTS product_locations (
  product_id          uuid        NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  location_id         text        NOT NULL,  -- '28250' | '28251' | '28252' | '28253'
  vetspire_product_id text        NOT NULL,
  enabled             boolean     NOT NULL DEFAULT true,
  synced_at           timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (product_id, location_id)
);

-- Fast lookup: "give me all enabled products at location X"
CREATE INDEX IF NOT EXISTS idx_product_locations_loc_enabled
  ON product_locations (location_id, enabled)
  WHERE enabled = true;

-- Fast lookup: reverse — "which locations is product X enabled at?"
CREATE INDEX IF NOT EXISTS idx_product_locations_product
  ON product_locations (product_id);
