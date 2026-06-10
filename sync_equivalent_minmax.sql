-- sync_equivalent_minmax.sql
-- Propagates qty_min / qty_max from tracked products to their
-- brand/generic equivalents at the same dose strength.
-- Also fixes known data errors (e.g. wrong dispensing_unit).
--
-- Run in Supabase SQL Editor.

-- ── Fix: Cerenia Injectable dispensing_unit is wrong (shows 'tablets') ────────
UPDATE public.products
SET dispensing_unit = 'mL'
WHERE name ILIKE '%cerenia%injectable%'
   OR name ILIKE '%cerenia%injection%';

-- ── MAROPITANT: tablets by dose ───────────────────────────────────────────────
-- 16mg tablets → min=8, max=32
UPDATE public.products SET qty_min = 8, qty_max = 32
WHERE (name ILIKE '%maropitant%16mg%' OR name ILIKE '%cerenia%16mg%' OR name ILIKE '%emeprev%16mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 24mg tablets → min=8, max=32
UPDATE public.products SET qty_min = 8, qty_max = 32
WHERE (name ILIKE '%maropitant%24mg%' OR name ILIKE '%cerenia%24mg%' OR name ILIKE '%emeprev%24mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 60mg tablets → min=8, max=32
UPDATE public.products SET qty_min = 8, qty_max = 32
WHERE (name ILIKE '%maropitant%60mg%' OR name ILIKE '%cerenia%60mg%' OR name ILIKE '%emeprev%60mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- Injectable 10mg/ml → min=10, max=40 mL
UPDATE public.products SET qty_min = 10, qty_max = 40, dispensing_unit = 'mL'
WHERE (name ILIKE '%maropitant%10mg/ml%' OR name ILIKE '%cerenia%injectable%' OR name ILIKE '%cerenia%injection%'
    OR name ILIKE '%emeprev%injectable%' OR name ILIKE '%emeprev%injection%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── KETAMINE: Injectable 100mg/ml → min=50, max=200 mL ───────────────────────
UPDATE public.products SET qty_min = 50, qty_max = 200, dispensing_unit = 'mL'
WHERE name ILIKE '%ketamine%'
  AND (name ILIKE '%100mg/ml%' OR name ILIKE '%100 mg/ml%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── DEXMEDETOMIDINE: 0.5mg/ml → min=10, max=40 mL ───────────────────────────
UPDATE public.products SET qty_min = 10, qty_max = 40, dispensing_unit = 'mL'
WHERE name ILIKE '%dexmedetomidine%'
  AND (name ILIKE '%0.5mg%' OR name ILIKE '%0.5 mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- Dexdomitor (brand name for dexmedetomidine 0.5mg/ml)
UPDATE public.products SET qty_min = 10, qty_max = 40, dispensing_unit = 'mL'
WHERE name ILIKE '%dexdomitor%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── PROPOFOL: 10mg/ml injectable ─────────────────────────────────────────────
UPDATE public.products SET qty_min = 40, qty_max = 160, dispensing_unit = 'mL'
WHERE name ILIKE '%propofol%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── BUPRENORPHINE: 0.3mg/ml → min=5, max=20 mL ──────────────────────────────
UPDATE public.products SET qty_min = 5, qty_max = 20, dispensing_unit = 'mL'
WHERE name ILIKE '%buprenorphine%0.3mg%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── BUTORPHANOL: 10mg/ml → min=50, max=150 mL ───────────────────────────────
UPDATE public.products SET qty_min = 50, qty_max = 150, dispensing_unit = 'mL'
WHERE name ILIKE '%butorphanol%10mg%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── HYDROMORPHONE: 2mg/ml → min=10, max=40 mL ───────────────────────────────
UPDATE public.products SET qty_min = 10, qty_max = 40, dispensing_unit = 'mL'
WHERE name ILIKE '%hydromorphone%2mg%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── GABAPENTIN: 100mg capsules → min=30, max=100 capsules ───────────────────
UPDATE public.products SET qty_min = 30, qty_max = 100, dispensing_unit = 'capsules'
WHERE name ILIKE '%gabapentin%100mg%'
  AND (name ILIKE '%cap%' OR name ILIKE '%tab%')
  AND name NOT ILIKE '%suspension%' AND name NOT ILIKE '%oral oil%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 300mg capsules → min=30, max=100 capsules
UPDATE public.products SET qty_min = 30, qty_max = 100, dispensing_unit = 'capsules'
WHERE name ILIKE '%gabapentin%300mg%'
  AND (name ILIKE '%cap%' OR name ILIKE '%tab%')
  AND name NOT ILIKE '%suspension%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── MELOXICAM: injectable → min=20, max=80 mL ───────────────────────────────
UPDATE public.products SET qty_min = 20, qty_max = 80, dispensing_unit = 'mL'
WHERE name ILIKE '%meloxicam%'
  AND (name ILIKE '%inject%' OR name ILIKE '%mg/ml%')
  AND name NOT ILIKE '%oral%' AND name NOT ILIKE '%suspension%'
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── CARPROFEN: tablets by dose ───────────────────────────────────────────────
-- 50mg tablets (Rimadyl, Carprovet, Novox) → min=30, max=180 tablets
UPDATE public.products SET qty_min = 30, qty_max = 180, dispensing_unit = 'tablets'
WHERE (name ILIKE '%carprofen%50mg%' OR name ILIKE '%rimadyl%50mg%' OR name ILIKE '%carprovet%50mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 25mg tablets → min=30, max=180
UPDATE public.products SET qty_min = 30, qty_max = 180, dispensing_unit = 'tablets'
WHERE (name ILIKE '%carprofen%25mg%' OR name ILIKE '%rimadyl%25mg%' OR name ILIKE '%carprovet%25mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 75mg tablets → min=30, max=180
UPDATE public.products SET qty_min = 30, qty_max = 180, dispensing_unit = 'tablets'
WHERE (name ILIKE '%carprofen%75mg%' OR name ILIKE '%rimadyl%75mg%' OR name ILIKE '%carprovet%75mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- 100mg tablets → min=30, max=180
UPDATE public.products SET qty_min = 30, qty_max = 180, dispensing_unit = 'tablets'
WHERE (name ILIKE '%carprofen%100mg%' OR name ILIKE '%rimadyl%100mg%' OR name ILIKE '%carprovet%100mg%')
  AND (qty_min IS NULL OR qty_max IS NULL);

-- ── Verify results ───────────────────────────────────────────────────────────
SELECT name, dispensing_unit, qty_min, qty_max
FROM public.products
WHERE qty_min IS NOT NULL
ORDER BY name;
