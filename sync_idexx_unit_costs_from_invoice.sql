-- IDEXX In-House Diagnostic Products — Purchase Cost Sync
-- Source: IDEXX Invoice May 2026 (Invoice #s 3200390734, 3200390744, 3200827739, 3201441637, 3201821938)
-- Method: unit_price = invoice UNIT PRICE per package ÷ tests per package
-- These are per-test PURCHASE costs (not client charge prices).
-- 9 products matched by VetSpire product ID, 1 by name (SNAP Feline proBNP — no SKU in VetSpire).
-- Products not on this invoice (ALT, BUN, TT4, TBILI, 4DX, Feline Triple, Coag PT/aPTT, UA Strip) are unchanged.

BEGIN;

-- Pass 1: match by vetspire_product_id (most reliable)
UPDATE products SET
  unit_price = 9.15,
  price_year = '2026'
WHERE vetspire_product_id = 628267;  -- Catalyst PHOS (12) | $109.80/box ÷ 12

UPDATE products SET
  unit_price = 26.95,
  price_year = '2026'
WHERE vetspire_product_id = 1905936;  -- Catalyst Cortisol (6) | $161.70/EA ÷ 6

UPDATE products SET
  unit_price = 27.50,
  price_year = '2026'
WHERE vetspire_product_id = 1626175;  -- Catalyst PL (12) | $330.00/EA ÷ 12

UPDATE products SET
  unit_price = 55.65,
  price_year = '2026'
WHERE vetspire_product_id = 628245;  -- Catalyst Chem 17 CLIP (12) | $667.80/box ÷ 12

UPDATE products SET
  unit_price = 15.10,
  price_year = '2026'
WHERE vetspire_product_id = 628247;  -- Catalyst Lytes 4 CLIP (12) | $181.20/box ÷ 12

UPDATE products SET
  unit_price = 9.15,
  price_year = '2026'
WHERE vetspire_product_id = 628259;  -- Catalyst CREA (12) | $109.80/box ÷ 12

UPDATE products SET
  unit_price = 27.60,
  price_year = '2026'
WHERE vetspire_product_id = 628233;  -- SNAP Parvo Test (5) | $138.00/EA ÷ 5

UPDATE products SET
  unit_price = 37.95,
  price_year = '2026'
WHERE vetspire_product_id = 628246;  -- Catalyst Chem 10 CLIP (12) | $455.40/box ÷ 12

UPDATE products SET
  unit_price = 27.50,
  price_year = '2026'
WHERE vetspire_product_id = 628260;  -- Catalyst FRU Ser/Pl (6) | $165.00/EA ÷ 6

-- Pass 2: SNAP Feline proBNP Test — no SKU in VetSpire export, match by vetspire_product_id
UPDATE products SET
  unit_price = 28.40,
  price_year = '2026'
WHERE vetspire_product_id = 628237;  -- SNAP Feline proBNP Test (5) | $142.00/EA ÷ 5

-- Fallback by name for any of the above that didn't match on vetspire_product_id
UPDATE products SET
  unit_price = 9.15,    price_year = '2026'
WHERE name ILIKE '%catalyst%phos%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628267));

UPDATE products SET
  unit_price = 26.95,   price_year = '2026'
WHERE name ILIKE '%cortisol%'
  AND name ILIKE '%catalyst%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (1905936));

UPDATE products SET
  unit_price = 27.50,   price_year = '2026'
WHERE (name ILIKE '%catalyst%pancreatic%lipase%' OR name ILIKE '%catalyst%pl%')
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (1626175));

UPDATE products SET
  unit_price = 55.65,   price_year = '2026'
WHERE (name ILIKE '%catalyst%chem%17%' OR name ILIKE '%chem 17%')
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628245));

UPDATE products SET
  unit_price = 15.10,   price_year = '2026'
WHERE (name ILIKE '%catalyst%lyte%4%' OR name ILIKE '%lytes 4%')
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628247));

UPDATE products SET
  unit_price = 9.15,    price_year = '2026'
WHERE (name ILIKE '%catalyst%crea%' OR name ILIKE '%creatinine%')
  AND name ILIKE '%catalyst%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628259));

UPDATE products SET
  unit_price = 27.60,   price_year = '2026'
WHERE name ILIKE '%snap%parvo%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628233));

UPDATE products SET
  unit_price = 37.95,   price_year = '2026'
WHERE (name ILIKE '%catalyst%chem%10%' OR name ILIKE '%chem 10%')
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628246));

UPDATE products SET
  unit_price = 27.50,   price_year = '2026'
WHERE (name ILIKE '%fructosamine%' OR name ILIKE '%fru%ser%')
  AND name ILIKE '%catalyst%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628260));

UPDATE products SET
  unit_price = 28.40,   price_year = '2026'
WHERE name ILIKE '%snap%feline%probnp%'
  AND (vetspire_product_id IS NULL OR vetspire_product_id NOT IN (628237));

-- Verify
SELECT
  vetspire_product_id,
  name,
  unit_price,
  price_year
FROM products
WHERE vetspire_product_id IN (628267, 1905936, 1626175, 628245, 628247, 628259, 628233, 628246, 628260, 628237)
ORDER BY name;

COMMIT;
