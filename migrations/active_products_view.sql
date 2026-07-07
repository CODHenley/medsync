-- active_products: products that are enabled at one or more Scout locations.
-- Queries /rest/v1/active_products instead of /rest/v1/products to
-- automatically exclude anything deactivated in Vetspire.

CREATE OR REPLACE VIEW active_products AS
SELECT DISTINCT p.*
FROM products p
JOIN product_locations pl ON pl.product_id = p.id
WHERE pl.enabled = true;

-- Grant anon read access (mirrors what products table already allows)
GRANT SELECT ON active_products TO anon;
GRANT SELECT ON active_products TO authenticated;
