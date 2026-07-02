-- VetSpire unit cost sync — West Loop (location 24356)
-- All prices identical to Old Orchard; 9 WL-exclusive products added
-- NOTE: Maropitant Inj 10 mg/ml has a different VetSpire ID (646646, $70.90)
--       vs Old Orchard (2333592, $65.25) — different product entries in VetSpire
-- Run in: Supabase Dashboard → SQL Editor

BEGIN;

-- Step 1: Update by vetspire_product_id where already mapped
UPDATE public.products SET unit_price = 36.6,  price_year = '2026' WHERE vetspire_product_id = '628265';
UPDATE public.products SET unit_price = 64.25, price_year = '2026' WHERE vetspire_product_id = '837586';
UPDATE public.products SET unit_price = 10.42, price_year = '2026' WHERE vetspire_product_id = '646517';
UPDATE public.products SET unit_price = 10.28, price_year = '2026' WHERE vetspire_product_id = '646521';
UPDATE public.products SET unit_price = 15.34, price_year = '2026' WHERE vetspire_product_id = '667667';
UPDATE public.products SET unit_price = 18.4,  price_year = '2026' WHERE vetspire_product_id = '646459';
UPDATE public.products SET unit_price = 70.9,  price_year = '2026' WHERE vetspire_product_id = '646646';
UPDATE public.products SET unit_price = 10.91, price_year = '2026' WHERE vetspire_product_id = '2511275';
UPDATE public.products SET unit_price = 50.32, price_year = '2026' WHERE vetspire_product_id = '2334288';

-- Step 2: Map + update by name where vetspire_product_id not yet set
UPDATE public.products SET unit_price = 36.6,  vetspire_product_id = '628265', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Catalyst Ammonia (NH3)');
UPDATE public.products SET unit_price = 64.25, vetspire_product_id = '837586', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Diclofenac Opthalmic Solu 0.1% (5 ml)');
UPDATE public.products SET unit_price = 10.42, vetspire_product_id = '646517', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Famotidine 20 mg tablets');
UPDATE public.products SET unit_price = 10.28, vetspire_product_id = '646521', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Furosemide 20 mg tablets');
UPDATE public.products SET unit_price = 15.34, vetspire_product_id = '667667', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Hill''s i/d Canine Chicken and Vegetable Stew (12.5 oz)');
UPDATE public.products SET unit_price = 18.4,  vetspire_product_id = '646459', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Hydrocodone 5 mg /Homatropine 1.5 mg tablets');
UPDATE public.products SET unit_price = 70.9,  vetspire_product_id = '646646', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Maropitant Inj 10 mg/ml');
UPDATE public.products SET unit_price = 10.91, vetspire_product_id = '2511275', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Proviable Fiber / tsp');
UPDATE public.products SET unit_price = 50.32, vetspire_product_id = '2334288', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('TrizULTRA+Keto Flush (4 oz)');

COMMIT;
