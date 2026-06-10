-- Set qty_min, qty_max, dispensing_unit, purchase_unit, package_size for tracked products
-- Values are in dispensing units (same as Vetspire). Adjust as needed.

UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=50,
      qty_min=50, qty_max=200
  WHERE name ILIKE '%acepromazine%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=20, qty_max=80
  WHERE name ILIKE '%alfaxalone%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=10,
      qty_min=10, qty_max=40
  WHERE name ILIKE '%atipamezole%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='bottle', package_size=100,
      qty_min=50, qty_max=200
  WHERE name ILIKE '%atropine%inject%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=1,
      qty_min=5, qty_max=20
  WHERE name ILIKE '%buprenorphine%0.3%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=50,
      qty_min=50, qty_max=150
  WHERE name ILIKE '%butorphanol%inject%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=10,
      qty_min=10, qty_max=40
  WHERE name ILIKE '%dexmedetomidine%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=10, qty_max=40
  WHERE name ILIKE '%hydromorphone%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=50,
      qty_min=50, qty_max=200
  WHERE name ILIKE '%ketamine%10mg%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=10, qty_max=40
  WHERE name ILIKE '%maropitant%inject%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=10, qty_max=40
  WHERE name ILIKE '%maropitant citrate 10%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='bottle', package_size=50,
      qty_min=20, qty_max=80
  WHERE name ILIKE '%meloxicam%inject%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=20, qty_max=60
  WHERE name ILIKE '%ondansetron%inject%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=20,
      qty_min=40, qty_max=160
  WHERE name ILIKE '%propofol%10mg%';
UPDATE public.products
  SET dispensing_unit='mL', purchase_unit='vial', package_size=25,
      qty_min=25, qty_max=75
  WHERE name ILIKE '%telazol%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=180,
      qty_min=30, qty_max=180
  WHERE name ILIKE '%carprofen%50mg%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=180,
      qty_min=30, qty_max=180
  WHERE name ILIKE '%carprofen%100mg%';
UPDATE public.products
  SET dispensing_unit='capsules', purchase_unit='bottle', package_size=100,
      qty_min=30, qty_max=100
  WHERE name ILIKE '%gabapentin%100mg%cap%';
UPDATE public.products
  SET dispensing_unit='capsules', purchase_unit='bottle', package_size=100,
      qty_min=30, qty_max=100
  WHERE name ILIKE '%gabapentin%100 mg%cap%';
UPDATE public.products
  SET dispensing_unit='capsules', purchase_unit='bottle', package_size=100,
      qty_min=30, qty_max=100
  WHERE name ILIKE '%gabapentin%300mg%cap%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='box', package_size=4,
      qty_min=8, qty_max=32
  WHERE name ILIKE '%maropitant%tab%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30,
      qty_min=20, qty_max=60
  WHERE name ILIKE '%meloxicam%tab%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100,
      qty_min=20, qty_max=60
  WHERE name ILIKE '%metronidazole%tab%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100,
      qty_min=30, qty_max=100
  WHERE name ILIKE '%tramadol%50mg%';
UPDATE public.products
  SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100,
      qty_min=20, qty_max=60
  WHERE name ILIKE '%trazodone%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=200, qty_max=600
  WHERE name ILIKE '%gauze%4x4%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=200, qty_max=600
  WHERE name ILIKE '%gauze%4 x 4%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=200, qty_max=600
  WHERE name ILIKE '%syringe%3cc%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=200, qty_max=600
  WHERE name ILIKE '%syringe%3 cc%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=200, qty_max=600
  WHERE name ILIKE '%syringe%3ml%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=100, qty_max=300
  WHERE name ILIKE '%needle%18g%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=100, qty_max=300
  WHERE name ILIKE '%needle%20g%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=100,
      qty_min=100, qty_max=300
  WHERE name ILIKE '%needle%22g%';
UPDATE public.products
  SET dispensing_unit='each', purchase_unit='box', package_size=50,
      qty_min=50, qty_max=150
  WHERE name ILIKE '%iv catheter%';

-- Verify
SELECT name, dispensing_unit, purchase_unit, package_size, qty_min, qty_max
FROM public.products WHERE qty_min IS NOT NULL ORDER BY name;