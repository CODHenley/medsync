-- IDEXX In-House Diagnostic Products — Purchase Cost Sync (v2)
-- Source: IDEXX Invoice May 2026 (Invoice #s 3200390734, 3200390744, 3200827739, 3201441637, 3201821938)
-- Method: unit_price = invoice UNIT PRICE per package ÷ tests per package
-- Matching by exact product name as it appears in MedSync (from Price Comparison view).

BEGIN;

UPDATE products SET unit_price = 55.65, price_year = '2026' WHERE name = 'Catalyst Chem 17';           -- $667.80/box ÷ 12
UPDATE products SET unit_price = 37.95, price_year = '2026' WHERE name = 'Catalyst Chem 10';           -- $455.40/box ÷ 12
UPDATE products SET unit_price = 15.10, price_year = '2026' WHERE name = 'Catalyst Lytes 4';           -- $181.20/box ÷ 12
UPDATE products SET unit_price = 27.50, price_year = '2026' WHERE name = 'Catalyst Pancreatic Lipase (PL)';  -- $330.00/ea ÷ 12
UPDATE products SET unit_price =  9.15, price_year = '2026' WHERE name ILIKE '%catalyst%phos%';         -- $109.80/box ÷ 12
UPDATE products SET unit_price =  9.15, price_year = '2026' WHERE name ILIKE '%catalyst%creatinine%';   -- $109.80/box ÷ 12
UPDATE products SET unit_price = 26.95, price_year = '2026' WHERE name ILIKE '%catalyst%cortisol%';     -- $161.70/ea ÷ 6
UPDATE products SET unit_price = 27.50, price_year = '2026' WHERE name ILIKE '%catalyst%fructosamine%'; -- $165.00/ea ÷ 6
UPDATE products SET unit_price = 27.60, price_year = '2026' WHERE name ILIKE '%snap%parvo%';            -- $138.00/ea ÷ 5
UPDATE products SET unit_price = 28.40, price_year = '2026' WHERE name ILIKE '%snap%feline%probnp%';    -- $142.00/ea ÷ 5

-- Verify — should show 10 rows with updated prices
SELECT name, unit_price, price_year
FROM products
WHERE name IN ('Catalyst Chem 17','Catalyst Chem 10','Catalyst Lytes 4','Catalyst Pancreatic Lipase (PL)')
   OR name ILIKE '%catalyst%phos%'
   OR name ILIKE '%catalyst%creatinine%'
   OR name ILIKE '%catalyst%cortisol%'
   OR name ILIKE '%catalyst%fructosamine%'
   OR name ILIKE '%snap%parvo%'
   OR name ILIKE '%snap%feline%probnp%'
ORDER BY name;

COMMIT;
