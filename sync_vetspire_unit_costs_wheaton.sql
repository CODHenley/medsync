-- VetSpire unit cost sync — Wheaton (location 28253)
-- All prices identical to other locations; 3 Wheaton-exclusive products added
-- Run in: Supabase Dashboard → SQL Editor

BEGIN;

-- Step 1: Update by vetspire_product_id where already mapped
UPDATE public.products SET unit_price = 260.0,  price_year = '2026' WHERE vetspire_product_id = '2549598';
UPDATE public.products SET unit_price = 13.06,  price_year = '2026' WHERE vetspire_product_id = '2520067';
UPDATE public.products SET unit_price = 109.97, price_year = '2026' WHERE vetspire_product_id = '893822';

-- Step 2: Map + update by name where vetspire_product_id not yet set
UPDATE public.products SET unit_price = 260.0,  vetspire_product_id = '2549598', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Rabies Spec Collect/Submission (DuPage County)');
UPDATE public.products SET unit_price = 13.06,  vetspire_product_id = '2520067', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Royal Canin Feline SO (3 oz)');
UPDATE public.products SET unit_price = 109.97, vetspire_product_id = '893822',  price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Zenalpha 0.5 mg/ml');

COMMIT;
