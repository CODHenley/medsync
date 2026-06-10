-- Populate dispensing_unit for Vetspire-tracked products
-- These are the units Vetspire uses for inventory tracking (how you sell/waste/count)

UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%propofol%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%ketamine%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%dexmedetomidine%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%buprenorphine%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%buprenorphine%' AND name ILIKE '%0.3%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%hydromorphone%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%acepromazine%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%maropitant%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%cerenia%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%meloxicam%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%ondansetron%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%butorphanol%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%atropine%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%epinephrine%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%lidocaine%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%saline%' AND name ILIKE '%inj%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%lactated ringer%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%LRS%';
UPDATE public.products SET dispensing_unit = 'mL'        WHERE name ILIKE '%fluids%' AND name ILIKE '%IV%';

UPDATE public.products SET dispensing_unit = 'capsules'  WHERE name ILIKE '%gabapentin%' AND name ILIKE '%cap%';
UPDATE public.products SET dispensing_unit = 'capsules'  WHERE name ILIKE '%doxycycline%' AND name ILIKE '%cap%';
UPDATE public.products SET dispensing_unit = 'capsules'  WHERE name ILIKE '%amoxicillin%' AND name ILIKE '%cap%';
UPDATE public.products SET dispensing_unit = 'capsules'  WHERE name ILIKE '%metronidazole%' AND name ILIKE '%cap%';

UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%gabapentin%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%carprofen%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%tramadol%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%maropitant%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%cerenia%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%meloxicam%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%metronidazole%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%onsior%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%trazodone%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%amoxicillin%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%clavamox%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%doxycycline%' AND name ILIKE '%tab%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%prednisone%';
UPDATE public.products SET dispensing_unit = 'tablets'   WHERE name ILIKE '%prednisolone%' AND name ILIKE '%tab%';

UPDATE public.products SET dispensing_unit = 'doses'     WHERE name ILIKE '%vaccine%';
UPDATE public.products SET dispensing_unit = 'doses'     WHERE name ILIKE '%vanguard%';
UPDATE public.products SET dispensing_unit = 'doses'     WHERE name ILIKE '%rabies%';
UPDATE public.products SET dispensing_unit = 'doses'     WHERE name ILIKE '%bordetella%';
UPDATE public.products SET dispensing_unit = 'doses'     WHERE name ILIKE '%leptospira%';

UPDATE public.products SET dispensing_unit = 'mg'        WHERE name ILIKE '%fentanyl%' AND name ILIKE '%patch%';
UPDATE public.products SET dispensing_unit = 'units'     WHERE name ILIKE '%insulin%';

-- Verify: show all Vetspire-tracked products with their dispensing units
SELECT name, dispensing_unit, qty_min, qty_max
FROM public.products
WHERE qty_min IS NOT NULL
ORDER BY name;
