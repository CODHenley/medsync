-- Corrected product unit updates using exact Supabase names
-- Verify package_size against your actual product packaging before running.

UPDATE products SET dispensing_unit = 'mL', package_size = 50 WHERE name = 'Acepromazine 10mg/ml';
UPDATE products SET dispensing_unit = 'mL', package_size = 1.0 WHERE name = 'Buprenorphine 0.3mg/ml';
UPDATE products SET dispensing_unit = 'tablets', package_size = 180 WHERE name = 'Carprofen 50mg tabs';
UPDATE products SET dispensing_unit = 'mL', package_size = 10.0 WHERE name = 'Dexmedetomidine 0.5mg/ml';
UPDATE products SET dispensing_unit = 'capsules', package_size = 500.0 WHERE name = 'Gabapentin 100mg caps';
UPDATE products SET dispensing_unit = 'mL', package_size = 20.0 WHERE name = 'Hydromorphone 2mg/ml';
UPDATE products SET dispensing_unit = 'mL', package_size = 10.0 WHERE name = 'Ketamine HCl 10mg/ml';

-- Keyword-based fallback for remaining products (review before running)
UPDATE products SET dispensing_unit = 'mL', package_size = 20 WHERE name ILIKE '%maropitant%' AND dispensing_unit IS NULL;
UPDATE products SET dispensing_unit = 'tablets', package_size = 30 WHERE name ILIKE '%ondansetron%' AND dispensing_unit IS NULL;
UPDATE products SET dispensing_unit = 'mL', package_size = 50 WHERE name ILIKE '%meloxicam%' AND dispensing_unit IS NULL;
UPDATE products SET dispensing_unit = 'doses', package_size = 25 WHERE name ILIKE '%vanguard%' AND dispensing_unit IS NULL;
UPDATE products SET dispensing_unit = 'mL', package_size = 10 WHERE name ILIKE '%alfaxalone%' AND dispensing_unit IS NULL;

SELECT name, dispensing_unit, package_size FROM products ORDER BY name;