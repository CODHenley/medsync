-- Find exact product names in Supabase for the drugs we need to set min/max on
SELECT id, name, dispensing_unit, purchase_unit, package_size, qty_min
FROM products
WHERE
  name ILIKE '%ketamine%' OR
  name ILIKE '%propofol%' OR
  name ILIKE '%dexmedetomidine%' OR
  name ILIKE '%buprenorphine%' OR
  name ILIKE '%cerenia%' OR
  name ILIKE '%maropitant%' OR
  name ILIKE '%gabapentin%' OR
  name ILIKE '%carprofen%' OR
  name ILIKE '%tramadol%' OR
  name ILIKE '%hydromorphone%' OR
  name ILIKE '%acepromazine%' OR
  name ILIKE '%ondansetron%' OR
  name ILIKE '%meloxicam%' OR
  name ILIKE '%butorphanol%'
ORDER BY name;
