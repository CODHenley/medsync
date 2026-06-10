-- Step 1: Clear ALL qty_min / qty_max (removes false positives from bulk update)
UPDATE public.products SET qty_min = NULL, qty_max = NULL;

-- Step 2: Set ONLY the confirmed Vetspire-tracked products
-- Using specific name patterns to avoid duplicates

-- ── Injectables ────────────────────────────────────────────────────────────────
UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=50,
  qty_min=50, qty_max=200
WHERE name ILIKE '%acepromazine%10mg%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=20,
  qty_min=20, qty_max=80
WHERE name ILIKE '%alfaxalone%10mg%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=1,
  qty_min=5, qty_max=20
WHERE name = 'Buprenorphine 0.3mg/ml';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=50,
  qty_min=50, qty_max=150
WHERE name ILIKE '%butorphanol%tartrate%inject%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=10,
  qty_min=10, qty_max=40
WHERE name ILIKE '%dexmedetomidine%0.5%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=20,
  qty_min=10, qty_max=40
WHERE name ILIKE '%hydromorphone%2mg%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=50,
  qty_min=50, qty_max=200
WHERE name ILIKE '%ketamine%10mg%'
  AND name NOT ILIKE '%label%'
  AND name NOT ILIKE '%100mg%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=20,
  qty_min=10, qty_max=40
WHERE name ILIKE '%maropitant citrate 10mg%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='bottle', package_size=50,
  qty_min=20, qty_max=80
WHERE name ILIKE '%meloxicam%5mg%inject%'
   OR (name ILIKE '%meloxicam%inj%' AND name ILIKE '%5mg%');

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=20,
  qty_min=20, qty_max=60
WHERE name ILIKE '%ondansetron%2mg%inject%';

UPDATE public.products SET
  dispensing_unit='mL', purchase_unit='vial', package_size=20,
  qty_min=40, qty_max=160
WHERE name ILIKE '%propofol%10mg%'
  AND name NOT ILIKE '%label%'
  AND name NOT ILIKE '%syringe%';

-- ── Oral medications ───────────────────────────────────────────────────────────
UPDATE public.products SET
  dispensing_unit='tablets', purchase_unit='bottle', package_size=180,
  qty_min=30, qty_max=180
WHERE name ILIKE '%carprofen%50mg%chewable%'
   OR name ILIKE '%carprofen%50mg%tab%';

UPDATE public.products SET
  dispensing_unit='capsules', purchase_unit='bottle', package_size=100,
  qty_min=30, qty_max=100
WHERE name ILIKE '%gabapentin%100mg%cap%'
   OR name ILIKE '%gabapentin%100 mg%cap%';

UPDATE public.products SET
  dispensing_unit='tablets', purchase_unit='box', package_size=4,
  qty_min=8, qty_max=32
WHERE name ILIKE '%maropitant%tab%'
  AND name NOT ILIKE '%inject%';

UPDATE public.products SET
  dispensing_unit='tablets', purchase_unit='bottle', package_size=100,
  qty_min=30, qty_max=100
WHERE name ILIKE '%tramadol%50mg%';

-- ── Vaccines ───────────────────────────────────────────────────────────────────
UPDATE public.products SET
  dispensing_unit='doses', purchase_unit='box', package_size=25,
  qty_min=25, qty_max=75
WHERE name ILIKE '%vanguard%dapp%';

-- ── Supplies ───────────────────────────────────────────────────────────────────
UPDATE public.products SET
  dispensing_unit='each', purchase_unit='box', package_size=100,
  qty_min=200, qty_max=600
WHERE name ILIKE '%gauze%4%x%4%'
   OR name ILIKE '%gauze%4x4%';

UPDATE public.products SET
  dispensing_unit='each', purchase_unit='box', package_size=100,
  qty_min=200, qty_max=600
WHERE (name ILIKE '%syringe%3cc%' OR name ILIKE '%syringe%3 cc%' OR name ILIKE '%syringe%3ml%')
  AND name NOT ILIKE '%needle%';

UPDATE public.products SET
  dispensing_unit='each', purchase_unit='box', package_size=100,
  qty_min=200, qty_max=600
WHERE name ILIKE '%exam glove%medium%'
   OR name ILIKE '%glove%medium%' AND name ILIKE '%exam%';

-- ── Verify: show all tracked products ─────────────────────────────────────────
SELECT name, dispensing_unit, purchase_unit, package_size, qty_min, qty_max
FROM public.products
WHERE qty_min IS NOT NULL
ORDER BY dispensing_unit, name;
