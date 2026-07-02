-- VetSpire unit cost sync — Lincoln Park (location 23083)
-- All prices identical to Old Orchard; only 6 LP-exclusive products added
-- Run in: Supabase Dashboard → SQL Editor

BEGIN;

-- Step 1: Update by vetspire_product_id where already mapped
UPDATE public.products SET unit_price = 17.78, price_year = '2026' WHERE vetspire_product_id = '646621';
UPDATE public.products SET unit_price = 13.01, price_year = '2026' WHERE vetspire_product_id = '646480';
UPDATE public.products SET unit_price = 11.12, price_year = '2026' WHERE vetspire_product_id = '646493';
UPDATE public.products SET unit_price = 64.25, price_year = '2026' WHERE vetspire_product_id = '837586';
UPDATE public.products SET unit_price = 10.91, price_year = '2026' WHERE vetspire_product_id = '2511275';
UPDATE public.products SET unit_price = 66.53, price_year = '2026' WHERE vetspire_product_id = '1382123';

-- Step 2: Map + update by name where vetspire_product_id not yet set
UPDATE public.products SET unit_price = 17.78, vetspire_product_id = '646621', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Acepromazine Inj 10 mg/ml');
UPDATE public.products SET unit_price = 13.01, vetspire_product_id = '646480', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Azithromycin 250 mg tablets');
UPDATE public.products SET unit_price = 11.12, vetspire_product_id = '646493', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Ciprofloxacin 500 mg tablets');
UPDATE public.products SET unit_price = 64.25, vetspire_product_id = '837586', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Diclofenac Opthalmic Solu 0.1% (5 ml)');
UPDATE public.products SET unit_price = 10.91, vetspire_product_id = '2511275', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Proviable Fiber / tsp');
UPDATE public.products SET unit_price = 66.53, vetspire_product_id = '1382123', price_year = '2026' WHERE vetspire_product_id IS NULL AND lower(trim(name)) = lower('Zymox Otic with 1% Hydrocortisone (1.25 oz)');

COMMIT;
