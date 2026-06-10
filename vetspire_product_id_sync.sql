-- ============================================================
-- vetspire_product_id_sync.sql
-- Maps MedSync products to Vetspire product IDs + canonical names
-- Enables exact snapshot lookup instead of fuzzy name matching
-- ============================================================

-- STEP 1: Add columns
ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS vetspire_product_id BIGINT,
  ADD COLUMN IF NOT EXISTS vetspire_product_name TEXT;

CREATE INDEX IF NOT EXISTS idx_products_vetspire_name
  ON public.products (vetspire_product_name);

-- STEP 2: Map products

-- Albuterol HFA 90 mcg
UPDATE public.products
  SET vetspire_product_id = 646467,
      vetspire_product_name = 'Albuterol HFA 90 mcg'
  WHERE name ILIKE '%albuterol%'
  AND name ILIKE '%90 mcg%';

-- Alfaxalone Inj 10 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646620,
      vetspire_product_name = 'Alfaxalone Inj 10 mg/ml'
  WHERE name ILIKE '%alfaxalone%'
  AND name ILIKE '%10 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Aluminum Hydroxide 64 mg/ml solution
UPDATE public.products
  SET vetspire_product_id = 646468,
      vetspire_product_name = 'Aluminum Hydroxide 64 mg/ml solution'
  WHERE name ILIKE '%aluminum%'
  AND name ILIKE '%64 mg/ml%';

-- Amlodipine 2.5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646470,
      vetspire_product_name = 'Amlodipine 2.5 mg tablets'
  WHERE name ILIKE '%amlodipine%'
  AND name ILIKE '%2.5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Amp+Sulbactam Inj 30 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646622,
      vetspire_product_name = 'Amp+Sulbactam Inj 30 mg/ml (1.5 g vial)'
  WHERE name ILIKE '%amp+sulbactam%'
  AND name ILIKE '%30 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Animax Ointment
UPDATE public.products
  SET vetspire_product_id = 646607,
      vetspire_product_name = 'Animax Ointment (15 ml)'
  WHERE name ILIKE '%animax%'
  AND name ILIKE '%15%';

-- Apomorphine HCl 3 mg/ml
UPDATE public.products
  SET vetspire_product_id = 838397,
      vetspire_product_name = 'Apomorphine HCl 3 mg/ml'
  WHERE name ILIKE '%apomorphine%'
  AND name ILIKE '%3 mg/ml%';

-- Apoquel 16 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646477,
      vetspire_product_name = 'Apoquel 16 mg tablets'
  WHERE name ILIKE '%apoquel%'
  AND name ILIKE '%16 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Apoquel 3.6 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646478,
      vetspire_product_name = 'Apoquel 3.6 mg tablets'
  WHERE name ILIKE '%apoquel%'
  AND name ILIKE '%3.6 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Apoquel 5.4 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646479,
      vetspire_product_name = 'Apoquel 5.4 mg tablets'
  WHERE name ILIKE '%apoquel%'
  AND name ILIKE '%5.4 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Atipamezole HCl  Inj 5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646624,
      vetspire_product_name = 'Atipamezole HCl  Inj 5 mg/ml'
  WHERE name ILIKE '%atipamezole%'
  AND name ILIKE '%5 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Atropine Inj 0.54 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646625,
      vetspire_product_name = 'Atropine Inj 0.54 mg/ml'
  WHERE name ILIKE '%atropine%'
  AND name ILIKE '%0.54 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- BNP Opthalmic Ointment
UPDATE public.products
  SET vetspire_product_id = 646591,
      vetspire_product_name = 'BNP Opthalmic Ointment (3.5 gm)'
  WHERE name ILIKE '%bnp%'
  AND name ILIKE '%3%';

-- Baytril Otic
UPDATE public.products
  SET vetspire_product_id = 646601,
      vetspire_product_name = 'Baytril Otic (15 ml)'
  WHERE name ILIKE '%baytril%'
  AND name ILIKE '%otic%'
  AND name ILIKE '%15%';

-- Buprenorphine  Inj 0.3 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646612,
      vetspire_product_name = 'Buprenorphine  Inj 0.3 mg/ml'
  WHERE name ILIKE '%buprenorphine%'
  AND name ILIKE '%0.3 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Butorphanol Inj 10 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646613,
      vetspire_product_name = 'Butorphanol Inj 10 mg/ml'
  WHERE name ILIKE '%butorphanol%'
  AND name ILIKE '%10 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Calcium Gluconate 10% Inj
UPDATE public.products
  SET vetspire_product_id = 646627,
      vetspire_product_name = 'Calcium Gluconate 10% Inj (100 mg/ml)'
  WHERE name ILIKE '%calcium%'
  AND name ILIKE '%10%%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Carprofen 100 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646485,
      vetspire_product_name = 'Carprofen 100 mg tablets'
  WHERE name ILIKE '%carprofen%'
  AND name ILIKE '%100 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Carprofen 25 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646486,
      vetspire_product_name = 'Carprofen 25 mg tablets'
  WHERE name ILIKE '%carprofen%'
  AND name ILIKE '%25 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Carprofen 75 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646487,
      vetspire_product_name = 'Carprofen 75 mg tablets'
  WHERE name ILIKE '%carprofen%'
  AND name ILIKE '%75 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Catalyst Alkaline Aminotransferase
UPDATE public.products
  SET vetspire_product_id = 628252,
      vetspire_product_name = 'Catalyst Alkaline Aminotransferase (ALT)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(ALT)%' OR name ILIKE '% alt%' OR name ILIKE '% ALT%' OR name ILIKE '%:alt%');

-- Catalyst Blood Urea Nitrogen
UPDATE public.products
  SET vetspire_product_id = 628255,
      vetspire_product_name = 'Catalyst Blood Urea Nitrogen (BUN)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(BUN)%' OR name ILIKE '% bun%' OR name ILIKE '% BUN%' OR name ILIKE '%:bun%');

-- Catalyst Chem 10
UPDATE public.products
  SET vetspire_product_id = 628246,
      vetspire_product_name = 'Catalyst Chem 10'
  WHERE name ILIKE '%catalyst%'
  AND name ILIKE '%chem%'
  AND name ILIKE '%10%';

-- Catalyst Chem 17
UPDATE public.products
  SET vetspire_product_id = 628245,
      vetspire_product_name = 'Catalyst Chem 17'
  WHERE name ILIKE '%catalyst%'
  AND name ILIKE '%chem%'
  AND name ILIKE '%17%';

-- Catalyst Cortisol
UPDATE public.products
  SET vetspire_product_id = 1905936,
      vetspire_product_name = 'Catalyst Cortisol (CORT)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(CORT)%' OR name ILIKE '% cort%' OR name ILIKE '% CORT%' OR name ILIKE '%:cort%');

-- Catalyst Creatinine
UPDATE public.products
  SET vetspire_product_id = 628259,
      vetspire_product_name = 'Catalyst Creatinine (CREA)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(CREA)%' OR name ILIKE '% crea%' OR name ILIKE '% CREA%' OR name ILIKE '%:crea%');

-- Catalyst Fructosamine
UPDATE public.products
  SET vetspire_product_id = 628260,
      vetspire_product_name = 'Catalyst Fructosamine (FRU)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(FRU)%' OR name ILIKE '% fru%' OR name ILIKE '% FRU%' OR name ILIKE '%:fru%');

-- Catalyst Inorganic Phosphate
UPDATE public.products
  SET vetspire_product_id = 628267,
      vetspire_product_name = 'Catalyst Inorganic Phosphate (PHOS)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(PHOS)%' OR name ILIKE '% phos%' OR name ILIKE '% PHOS%' OR name ILIKE '%:phos%');

-- Catalyst Lytes 4
UPDATE public.products
  SET vetspire_product_id = 628247,
      vetspire_product_name = 'Catalyst Lytes 4'
  WHERE name ILIKE '%catalyst%'
  AND name ILIKE '%lytes%'
  AND name ILIKE '%4%';

-- Catalyst Pancreatic Lipase
UPDATE public.products
  SET vetspire_product_id = 1626175,
      vetspire_product_name = 'Catalyst Pancreatic Lipase  (PL)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%lipase%' OR name ILIKE '% pl%' OR name ILIKE '%pli%');

-- Catalyst Total Bilirubin
UPDATE public.products
  SET vetspire_product_id = 970360,
      vetspire_product_name = 'Catalyst Total Bilirubin (TBILI)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(TBILI)%' OR name ILIKE '% tbili%' OR name ILIKE '% TBILI%' OR name ILIKE '%:tbili%');

-- Catalyst Total T4
UPDATE public.products
  SET vetspire_product_id = 628271,
      vetspire_product_name = 'Catalyst Total T4 (TT4)'
  WHERE name ILIKE '%catalyst%'
  AND (name ILIKE '%(TT4)%' OR name ILIKE '% tt4%' OR name ILIKE '% TT4%' OR name ILIKE '%:tt4%');

-- Cefpodoxime 200 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646489,
      vetspire_product_name = 'Cefpodoxime 200 mg tablets'
  WHERE name ILIKE '%cefpodoxime%'
  AND name ILIKE '%200 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Cephalexin 250 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646490,
      vetspire_product_name = 'Cephalexin 250 mg capsules'
  WHERE name ILIKE '%cephalexin%'
  AND name ILIKE '%250 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Cephalexin 500 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646491,
      vetspire_product_name = 'Cephalexin 500 mg capsules'
  WHERE name ILIKE '%cephalexin%'
  AND name ILIKE '%500 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Claro Otic
UPDATE public.products
  SET vetspire_product_id = 646602,
      vetspire_product_name = 'Claro Otic (1 ml)'
  WHERE name ILIKE '%claro%'
  AND name ILIKE '%otic%';

-- Clavacillin  Susp 62.5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646476,
      vetspire_product_name = 'Clavacillin  Susp 62.5 mg/ml (15 ml bottle)'
  WHERE name ILIKE '%clavacillin%'
  AND name ILIKE '%62.5 mg/ml%';

-- Clavacillin 125 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646472,
      vetspire_product_name = 'Clavacillin 125 mg tablets'
  WHERE name ILIKE '%clavacillin%'
  AND name ILIKE '%125 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Clavacillin 250 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646473,
      vetspire_product_name = 'Clavacillin 250 mg tablets'
  WHERE name ILIKE '%clavacillin%'
  AND name ILIKE '%250 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Clavacillin 375 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646474,
      vetspire_product_name = 'Clavacillin 375 mg tablets'
  WHERE name ILIKE '%clavacillin%'
  AND name ILIKE '%375 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Clavacillin 62.5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646475,
      vetspire_product_name = 'Clavacillin 62.5 mg tablets'
  WHERE name ILIKE '%clavacillin%'
  AND name ILIKE '%62.5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Clindamycin 150 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646494,
      vetspire_product_name = 'Clindamycin 150 mg capsules'
  WHERE name ILIKE '%clindamycin%'
  AND name ILIKE '%150 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Clindamycin Susp 25 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646496,
      vetspire_product_name = 'Clindamycin Susp 25 mg/ml (20 ml bottle)'
  WHERE name ILIKE '%clindamycin%'
  AND name ILIKE '%25 mg/ml%';

-- Coag Dx Citrate Activated Partial Thromboplastin Time
UPDATE public.products
  SET vetspire_product_id = 628241,
      vetspire_product_name = 'Coag Dx Citrate Activated Partial Thromboplastin Time (aPTT)'
  WHERE name ILIKE '%coag%'
  AND name ILIKE '%citrate%';

-- Coag Dx Citrate Prothrombin Time
UPDATE public.products
  SET vetspire_product_id = 628240,
      vetspire_product_name = 'Coag Dx Citrate Prothrombin Time (PT)'
  WHERE name ILIKE '%coag%'
  AND (name ILIKE '%(PT)%' OR name ILIKE '% pt%' OR name ILIKE '% PT%' OR name ILIKE '%:pt%');

-- Cytopoint 10 mg
UPDATE public.products
  SET vetspire_product_id = 646655,
      vetspire_product_name = 'Cytopoint 10 mg (1 ml vial)'
  WHERE name ILIKE '%cytopoint%'
  AND name ILIKE '%10 mg%';

-- Cytopoint 20 mg
UPDATE public.products
  SET vetspire_product_id = 646656,
      vetspire_product_name = 'Cytopoint 20 mg (1 ml vial)'
  WHERE name ILIKE '%cytopoint%'
  AND name ILIKE '%20 mg%';

-- Cytopoint 30 mg
UPDATE public.products
  SET vetspire_product_id = 646657,
      vetspire_product_name = 'Cytopoint 30 mg (1 ml vial)'
  WHERE name ILIKE '%cytopoint%'
  AND name ILIKE '%30 mg%';

-- Cytopoint 40 mg
UPDATE public.products
  SET vetspire_product_id = 646658,
      vetspire_product_name = 'Cytopoint 40 mg (1 ml vial)'
  WHERE name ILIKE '%cytopoint%'
  AND name ILIKE '%40 mg%';

-- Dexamethasone-SP Inj 4 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646629,
      vetspire_product_name = 'Dexamethasone-SP Inj 4 mg/ml'
  WHERE name ILIKE '%dexamethasone-sp%'
  AND name ILIKE '%4 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Dexmedetomidine Inj 0.5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646631,
      vetspire_product_name = 'Dexmedetomidine Inj 0.5 mg/ml'
  WHERE name ILIKE '%dexmedetomidine%'
  AND name ILIKE '%0.5 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Dextrose Solu Inj 50%
UPDATE public.products
  SET vetspire_product_id = 646632,
      vetspire_product_name = 'Dextrose Solu Inj 50%'
  WHERE name ILIKE '%dextrose%'
  AND name ILIKE '%50%%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Diclofenac Opthalmic Solu 0.1%
UPDATE public.products
  SET vetspire_product_id = 837586,
      vetspire_product_name = 'Diclofenac Opthalmic Solu 0.1% (5 ml)'
  WHERE name ILIKE '%diclofenac%'
  AND name ILIKE '%0.1%%';

-- Diphenhydramine 25 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646505,
      vetspire_product_name = 'Diphenhydramine 25 mg capsules'
  WHERE name ILIKE '%diphenhydramine%'
  AND name ILIKE '%25 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Diphenhydramine 50 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646506,
      vetspire_product_name = 'Diphenhydramine 50 mg capsules'
  WHERE name ILIKE '%diphenhydramine%'
  AND name ILIKE '%50 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Diphenhydramine Inj 50 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646633,
      vetspire_product_name = 'Diphenhydramine Inj 50 mg/ml'
  WHERE name ILIKE '%diphenhydramine%'
  AND name ILIKE '%50 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Diphenhydramine Syrup 12.5 mg/5 ml
UPDATE public.products
  SET vetspire_product_id = 646504,
      vetspire_product_name = 'Diphenhydramine Syrup 12.5 mg/5 ml  '
  WHERE name ILIKE '%diphenhydramine%'
  AND name ILIKE '%12.5 mg%';

-- Dorzolamide Timolol 2-0.5% Solu
UPDATE public.products
  SET vetspire_product_id = 646598,
      vetspire_product_name = 'Dorzolamide Timolol 2-0.5% Solu (10 ml)'
  WHERE name ILIKE '%dorzolamide%'
  AND name ILIKE '%0.5%%';

-- Douxo S3 PYO Mousse
UPDATE public.products
  SET vetspire_product_id = 646684,
      vetspire_product_name = 'Douxo S3 PYO Mousse (5.1 oz)'
  WHERE name ILIKE '%douxo%'
  AND name ILIKE '%mousse%'
  AND name ILIKE '%5%';

-- Douxo S3 PYO Shampoo
UPDATE public.products
  SET vetspire_product_id = 646683,
      vetspire_product_name = 'Douxo S3 PYO Shampoo (6.7 oz)'
  WHERE name ILIKE '%douxo%'
  AND name ILIKE '%shampoo%'
  AND name ILIKE '%6%';

-- Douxo S3 PYO Wipes
UPDATE public.products
  SET vetspire_product_id = 646685,
      vetspire_product_name = 'Douxo S3 PYO Wipes (30 ct)'
  WHERE name ILIKE '%douxo%'
  AND name ILIKE '%wipes%'
  AND name ILIKE '%30%';

-- Doxycycline 100 mg tablets
UPDATE public.products
  SET vetspire_product_id = 845001,
      vetspire_product_name = 'Doxycycline 100 mg tablets'
  WHERE name ILIKE '%doxycycline%'
  AND name ILIKE '%100 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Doxycycline Solu 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 845776,
      vetspire_product_name = 'Doxycycline Solu 100 mg/ml'
  WHERE name ILIKE '%doxycycline%'
  AND name ILIKE '%100 mg/ml%';

-- E-Collar - 10 cm
UPDATE public.products
  SET vetspire_product_id = 1162107,
      vetspire_product_name = 'E-Collar - 10 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%10%';

-- E-Collar - 12 cm
UPDATE public.products
  SET vetspire_product_id = 646397,
      vetspire_product_name = 'E-Collar - 12 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%12%';

-- E-Collar - 15 cm
UPDATE public.products
  SET vetspire_product_id = 646398,
      vetspire_product_name = 'E-Collar - 15 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%15%';

-- E-Collar - 20 cm
UPDATE public.products
  SET vetspire_product_id = 646399,
      vetspire_product_name = 'E-Collar - 20 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%20%';

-- E-Collar - 25 cm
UPDATE public.products
  SET vetspire_product_id = 646400,
      vetspire_product_name = 'E-Collar - 25 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%25%';

-- E-Collar - 30 cm
UPDATE public.products
  SET vetspire_product_id = 646401,
      vetspire_product_name = 'E-Collar - 30 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%30%';

-- E-Collar - 7.5 cm
UPDATE public.products
  SET vetspire_product_id = 646403,
      vetspire_product_name = 'E-Collar - 7.5 cm'
  WHERE name ILIKE '%e-collar%'
  AND name ILIKE '%7%';

-- Elura 20 mg/ml
UPDATE public.products
  SET vetspire_product_id = 670553,
      vetspire_product_name = 'Elura 20 mg/ml (15 ml)'
  WHERE name ILIKE '%elura%'
  AND name ILIKE '%20 mg/ml%';

-- Endosorb Susp
UPDATE public.products
  SET vetspire_product_id = 1743751,
      vetspire_product_name = 'Endosorb Susp'
  WHERE name ILIKE '%endosorb%'
  AND name ILIKE '%susp%';

-- Endosorb Tablets
UPDATE public.products
  SET vetspire_product_id = 1067430,
      vetspire_product_name = 'Endosorb Tablets'
  WHERE name ILIKE '%endosorb%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Endotracheal Tube - 10 mm Cuffed
UPDATE public.products
  SET vetspire_product_id = 648662,
      vetspire_product_name = 'Endotracheal Tube - 10 mm Cuffed'
  WHERE name ILIKE '%endotracheal%'
  AND name ILIKE '%tube%'
  AND name ILIKE '%10%';

-- Endotracheal Tube - 10.5 mm Cuffed
UPDATE public.products
  SET vetspire_product_id = 648664,
      vetspire_product_name = 'Endotracheal Tube - 10.5 mm Cuffed'
  WHERE name ILIKE '%endotracheal%'
  AND name ILIKE '%tube%'
  AND name ILIKE '%10%';

-- Endotracheal Tube - 11.0 mm Cuffed
UPDATE public.products
  SET vetspire_product_id = 648666,
      vetspire_product_name = 'Endotracheal Tube - 11.0 mm Cuffed'
  WHERE name ILIKE '%endotracheal%'
  AND name ILIKE '%tube%'
  AND name ILIKE '%11%';

-- Endotracheal Tube - 3.0 mm Cuffed
UPDATE public.products
  SET vetspire_product_id = 648674,
      vetspire_product_name = 'Endotracheal Tube - 3.0 mm Cuffed'
  WHERE name ILIKE '%endotracheal%'
  AND name ILIKE '%tube%'
  AND name ILIKE '%3%';

-- Enrofloxacin 136 mg tablets
UPDATE public.products
  SET vetspire_product_id = 923212,
      vetspire_product_name = 'Enrofloxacin 136 mg tablets'
  WHERE name ILIKE '%enrofloxacin%'
  AND name ILIKE '%136 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Entyce 30 mg/ml
UPDATE public.products
  SET vetspire_product_id = 670551,
      vetspire_product_name = 'Entyce 30 mg/ml (15 ml)'
  WHERE name ILIKE '%entyce%'
  AND name ILIKE '%30 mg/ml%';

-- Epinephrine Inj 1 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646635,
      vetspire_product_name = 'Epinephrine Inj 1 mg/ml'
  WHERE name ILIKE '%epinephrine%'
  AND name ILIKE '%1 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Epiotic Advanced Ear Cleanser
UPDATE public.products
  SET vetspire_product_id = 646610,
      vetspire_product_name = 'Epiotic Advanced Ear Cleanser (8 oz)'
  WHERE name ILIKE '%epiotic%'
  AND name ILIKE '%advanced%'
  AND name ILIKE '%8%';

-- Erythromycin 0.5% Ophthalmic Ointment
UPDATE public.products
  SET vetspire_product_id = 1069602,
      vetspire_product_name = 'Erythromycin 0.5% Ophthalmic Ointment (3.5 gm)'
  WHERE name ILIKE '%erythromycin%'
  AND name ILIKE '%0.5%%';

-- Euthasol
UPDATE public.products
  SET vetspire_product_id = 1678115,
      vetspire_product_name = 'Euthasol'
  WHERE name ILIKE '%euthasol%';

-- Famotidine 10 mg tablets
UPDATE public.products
  SET vetspire_product_id = 981759,
      vetspire_product_name = 'Famotidine 10 mg tablets'
  WHERE name ILIKE '%famotidine%'
  AND name ILIKE '%10 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Famotidine 20 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646517,
      vetspire_product_name = 'Famotidine 20 mg tablets'
  WHERE name ILIKE '%famotidine%'
  AND name ILIKE '%20 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Famotidine Inj 10 mg/mL
UPDATE public.products
  SET vetspire_product_id = 646636,
      vetspire_product_name = 'Famotidine Inj 10 mg/mL'
  WHERE name ILIKE '%famotidine%'
  AND name ILIKE '%10 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Fenbendazole Susp 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646519,
      vetspire_product_name = 'Fenbendazole Susp 100 mg/ml'
  WHERE name ILIKE '%fenbendazole%'
  AND name ILIKE '%100 mg/ml%';

-- Flumazenil Inj  0.1 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646637,
      vetspire_product_name = 'Flumazenil Inj  0.1 mg/ml'
  WHERE name ILIKE '%flumazenil%'
  AND name ILIKE '%0.1 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Furosemide 12.5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646520,
      vetspire_product_name = 'Furosemide 12.5 mg tablets'
  WHERE name ILIKE '%furosemide%'
  AND name ILIKE '%12.5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Furosemide 20 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646521,
      vetspire_product_name = 'Furosemide 20 mg tablets'
  WHERE name ILIKE '%furosemide%'
  AND name ILIKE '%20 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Furosemide Inj 50 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646638,
      vetspire_product_name = 'Furosemide Inj 50 mg/ml'
  WHERE name ILIKE '%furosemide%'
  AND name ILIKE '%50 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Gabapentin 100 mg QuadTabs
UPDATE public.products
  SET vetspire_product_id = 868294,
      vetspire_product_name = 'Gabapentin 100 mg QuadTabs'
  WHERE name ILIKE '%gabapentin%'
  AND name ILIKE '%100 mg%';

-- Gabapentin 100 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646523,
      vetspire_product_name = 'Gabapentin 100 mg capsules'
  WHERE name ILIKE '%gabapentin%'
  AND name ILIKE '%100 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Gabapentin 300 mg capsules
UPDATE public.products
  SET vetspire_product_id = 646524,
      vetspire_product_name = 'Gabapentin 300 mg capsules'
  WHERE name ILIKE '%gabapentin%'
  AND name ILIKE '%300 mg%'
  AND (name ILIKE '%capsule%' OR name ILIKE '% cap%');

-- Gabapentin Solu 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646525,
      vetspire_product_name = 'Gabapentin Solu 100 mg/ml'
  WHERE name ILIKE '%gabapentin%'
  AND name ILIKE '%100 mg/ml%';

-- Hill's Canine Gastrointestinal Biome Chicken and Vegetable Stew
UPDATE public.products
  SET vetspire_product_id = 1933389,
      vetspire_product_name = 'Hill''s Canine Gastrointestinal Biome Chicken and Vegetable Stew (12.5oz)'
  WHERE name ILIKE '%hill''s%'
  AND name ILIKE '%canine%'
  AND name ILIKE '%12%';

-- Hill's Feline Gastrointestinal Biome
UPDATE public.products
  SET vetspire_product_id = 1848212,
      vetspire_product_name = 'Hill''s Feline Gastrointestinal Biome (2.9 oz)'
  WHERE name ILIKE '%hill''s%'
  AND name ILIKE '%feline%'
  AND name ILIKE '%2%';

-- Hill's c/d Feline Urinary Care
UPDATE public.products
  SET vetspire_product_id = 667670,
      vetspire_product_name = 'Hill''s c/d Feline Urinary Care (5.5 oz)'
  WHERE name ILIKE '%hill''s%'
  AND name ILIKE '%feline%'
  AND name ILIKE '%5%';

-- Hill's i/d Canine Chicken and Vegetable Stew
UPDATE public.products
  SET vetspire_product_id = 667667,
      vetspire_product_name = 'Hill''s i/d Canine Chicken and Vegetable Stew (12.5 oz)'
  WHERE name ILIKE '%hill''s%'
  AND name ILIKE '%canine%'
  AND name ILIKE '%12%';

-- Hill's i/d Canine Low Fat Stew
UPDATE public.products
  SET vetspire_product_id = 646677,
      vetspire_product_name = 'Hill''s i/d Canine Low Fat Stew (12.5 oz)'
  WHERE name ILIKE '%hill''s%'
  AND name ILIKE '%canine%'
  AND name ILIKE '%12%';

-- Hydrocodone 5 mg /Homatropine 1.5 mg Solu / 5ml
UPDATE public.products
  SET vetspire_product_id = 646458,
      vetspire_product_name = 'Hydrocodone 5 mg /Homatropine 1.5 mg Solu / 5ml'
  WHERE name ILIKE '%hydrocodone%'
  AND name ILIKE '%5 mg%';

-- Ketamine HCl Inj 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646616,
      vetspire_product_name = 'Ketamine HCl Inj 100 mg/ml'
  WHERE name ILIKE '%ketamine%'
  AND name ILIKE '%100 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Lactulose Solu 10 g/15 ml
UPDATE public.products
  SET vetspire_product_id = 646532,
      vetspire_product_name = 'Lactulose Solu 10 g/15 ml (32 oz)'
  WHERE name ILIKE '%lactulose%'
  AND name ILIKE '%solu%'
  AND name ILIKE '%10%';

-- Levetiracetam 750 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646530,
      vetspire_product_name = 'Levetiracetam 750 mg tablets'
  WHERE name ILIKE '%levetiracetam%'
  AND name ILIKE '%750 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Levetiracetam Solu 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646529,
      vetspire_product_name = 'Levetiracetam Solu 100 mg/ml (16 oz)'
  WHERE name ILIKE '%levetiracetam%'
  AND name ILIKE '%100 mg/ml%';

-- Lidocaine HCl 2%  Topical Solu
UPDATE public.products
  SET vetspire_product_id = 646531,
      vetspire_product_name = 'Lidocaine HCl 2%  Topical Solu (20 mg/ml)'
  WHERE name ILIKE '%lidocaine%'
  AND name ILIKE '%2%%';

-- Lidocaine HCl 2% Inj
UPDATE public.products
  SET vetspire_product_id = 646644,
      vetspire_product_name = 'Lidocaine HCl 2% Inj (20 mg/ml)'
  WHERE name ILIKE '%lidocaine%'
  AND name ILIKE '%2%%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Mannitol 20% Inj
UPDATE public.products
  SET vetspire_product_id = 646413,
      vetspire_product_name = 'Mannitol 20% Inj (200 mg/ml)'
  WHERE name ILIKE '%mannitol%'
  AND name ILIKE '%20%%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Maropitant 16 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646538,
      vetspire_product_name = 'Maropitant 16 mg tablets'
  WHERE name ILIKE '%maropitant%'
  AND name ILIKE '%16 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Maropitant 24 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646539,
      vetspire_product_name = 'Maropitant 24 mg tablets'
  WHERE name ILIKE '%maropitant%'
  AND name ILIKE '%24 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Maropitant 60 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646540,
      vetspire_product_name = 'Maropitant 60 mg tablets'
  WHERE name ILIKE '%maropitant%'
  AND name ILIKE '%60 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Maropitant Inj 10 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646646,
      vetspire_product_name = 'Maropitant Inj 10 mg/ml'
  WHERE name ILIKE '%maropitant%'
  AND name ILIKE '%10 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Meloxicam Susp 0.5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646542,
      vetspire_product_name = 'Meloxicam Susp 0.5 mg/ml'
  WHERE name ILIKE '%meloxicam%'
  AND name ILIKE '%0.5 mg/ml%';

-- Meloxicam Susp 1.5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646541,
      vetspire_product_name = 'Meloxicam Susp 1.5 mg/ml'
  WHERE name ILIKE '%meloxicam%'
  AND name ILIKE '%1.5 mg/ml%';

-- Methadone Inj 10 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646617,
      vetspire_product_name = 'Methadone Inj 10 mg/ml'
  WHERE name ILIKE '%methadone%'
  AND name ILIKE '%10 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Methimazole 5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646543,
      vetspire_product_name = 'Methimazole 5 mg tablets'
  WHERE name ILIKE '%methimazole%'
  AND name ILIKE '%5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Methocarbamol 500 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646544,
      vetspire_product_name = 'Methocarbamol 500 mg tablets'
  WHERE name ILIKE '%methocarbamol%'
  AND name ILIKE '%500 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Metronidazole 250 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646545,
      vetspire_product_name = 'Metronidazole 250 mg tablets'
  WHERE name ILIKE '%metronidazole%'
  AND name ILIKE '%250 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Metronidazole 500 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646546,
      vetspire_product_name = 'Metronidazole 500 mg tablets'
  WHERE name ILIKE '%metronidazole%'
  AND name ILIKE '%500 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Metronidazole Benzoate Sus 100 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646548,
      vetspire_product_name = 'Metronidazole Benzoate Sus 100 mg/ml'
  WHERE name ILIKE '%metronidazole%'
  AND name ILIKE '%100 mg/ml%';

-- Metronidazole Tiny Tabs 50 mg  tablets
UPDATE public.products
  SET vetspire_product_id = 646547,
      vetspire_product_name = 'Metronidazole Tiny Tabs 50 mg  tablets'
  WHERE name ILIKE '%metronidazole%'
  AND name ILIKE '%50 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Midazolam Inj 5 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646618,
      vetspire_product_name = 'Midazolam Inj 5 mg/ml'
  WHERE name ILIKE '%midazolam%'
  AND name ILIKE '%5 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Mirtazapine 7.5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 1140862,
      vetspire_product_name = 'Mirtazapine 7.5 mg tablets'
  WHERE name ILIKE '%mirtazapine%'
  AND name ILIKE '%7.5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Mirtazapine Transdermal Ointment 5 gm
UPDATE public.products
  SET vetspire_product_id = 646550,
      vetspire_product_name = 'Mirtazapine Transdermal Ointment 5 gm'
  WHERE name ILIKE '%mirtazapine%'
  AND name ILIKE '%transdermal%'
  AND name ILIKE '%5%';

-- Mometamax Susp
UPDATE public.products
  SET vetspire_product_id = 646604,
      vetspire_product_name = 'Mometamax Susp (15 gm)'
  WHERE name ILIKE '%mometamax%'
  AND name ILIKE '%susp%'
  AND name ILIKE '%15%';

-- NPD Ophthalmic Ointment
UPDATE public.products
  SET vetspire_product_id = 1333328,
      vetspire_product_name = 'NPD Ophthalmic Ointment (3.5g)'
  WHERE name ILIKE '%npd%'
  AND name ILIKE '%3.5g%'
  AND name ILIKE '%3%';

-- NPD Ophthalmic Susp
UPDATE public.products
  SET vetspire_product_id = 646599,
      vetspire_product_name = 'NPD Ophthalmic Susp (5 ml)'
  WHERE name ILIKE '%npd%'
  AND name ILIKE '%susp%'
  AND name ILIKE '%5%';

-- Naloxone Inj 0.4 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646647,
      vetspire_product_name = 'Naloxone Inj 0.4 mg/ml'
  WHERE name ILIKE '%naloxone%'
  AND name ILIKE '%0.4 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- No Flap Ear Wrap - Large
UPDATE public.products
  SET vetspire_product_id = 1069601,
      vetspire_product_name = 'No Flap Ear Wrap - Large'
  WHERE name ILIKE '%wrap%';

-- No Flap Ear Wrap - Medium
UPDATE public.products
  SET vetspire_product_id = 1069600,
      vetspire_product_name = 'No Flap Ear Wrap - Medium'
  WHERE name ILIKE '%wrap%';

-- No Flap Ear Wrap - Small
UPDATE public.products
  SET vetspire_product_id = 1069598,
      vetspire_product_name = 'No Flap Ear Wrap - Small'
  WHERE name ILIKE '%wrap%';

-- Ofloxacin 0.3% Ophthalmic Solu
UPDATE public.products
  SET vetspire_product_id = 646593,
      vetspire_product_name = 'Ofloxacin 0.3% Ophthalmic Solu (5 ml)'
  WHERE name ILIKE '%ofloxacin%'
  AND name ILIKE '%0.3%%';

-- Ondansetron 4 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646554,
      vetspire_product_name = 'Ondansetron 4 mg tablets'
  WHERE name ILIKE '%ondansetron%'
  AND name ILIKE '%4 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Ondansetron 8 mg tablets
UPDATE public.products
  SET vetspire_product_id = 771653,
      vetspire_product_name = 'Ondansetron 8 mg tablets'
  WHERE name ILIKE '%ondansetron%'
  AND name ILIKE '%8 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Ondansetron Inj 2 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646649,
      vetspire_product_name = 'Ondansetron Inj 2 mg/ml'
  WHERE name ILIKE '%ondansetron%'
  AND name ILIKE '%2 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Optixcare PLUS Eye Lube
UPDATE public.products
  SET vetspire_product_id = 646594,
      vetspire_product_name = 'Optixcare PLUS Eye Lube (20 gm)'
  WHERE name ILIKE '%optixcare%'
  AND name ILIKE '%plus%'
  AND name ILIKE '%20%';

-- Panacur C Canine 1 g
UPDATE public.products
  SET vetspire_product_id = 646556,
      vetspire_product_name = 'Panacur C Canine 1 g (3/box)'
  WHERE name ILIKE '%panacur%'
  AND name ILIKE '%canine%';

-- Panacur C Canine 2 g
UPDATE public.products
  SET vetspire_product_id = 646556,
      vetspire_product_name = 'Panacur C Canine 1 g (3/box)'
  WHERE name ILIKE '%panacur%'
  AND name ILIKE '%canine%'
  AND name ILIKE '%2%';

-- Panacur C Canine 4 g
UPDATE public.products
  SET vetspire_product_id = 646556,
      vetspire_product_name = 'Panacur C Canine 1 g (3/box)'
  WHERE name ILIKE '%panacur%'
  AND name ILIKE '%canine%'
  AND name ILIKE '%4%';

-- Pimobendan 2.5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646559,
      vetspire_product_name = 'Pimobendan 2.5 mg tablets'
  WHERE name ILIKE '%pimobendan%'
  AND name ILIKE '%2.5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Posatex Susp
UPDATE public.products
  SET vetspire_product_id = 646605,
      vetspire_product_name = 'Posatex Susp (15 gm)'
  WHERE name ILIKE '%posatex%'
  AND name ILIKE '%susp%'
  AND name ILIKE '%15%';

-- PredniSONE 10 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646568,
      vetspire_product_name = 'PredniSONE 10 mg tablets'
  WHERE name ILIKE '%prednisone%'
  AND name ILIKE '%10 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Prednisolone  Acetate 1% Opthalmic Susp
UPDATE public.products
  SET vetspire_product_id = 646596,
      vetspire_product_name = 'Prednisolone  Acetate 1% Opthalmic Susp (5 ml)'
  WHERE name ILIKE '%prednisolone%'
  AND name ILIKE '%1%%';

-- Prednisolone 5 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646566,
      vetspire_product_name = 'Prednisolone 5 mg tablets'
  WHERE name ILIKE '%prednisolone%'
  AND name ILIKE '%5 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Prednisolone Solu 15 mg/ 5 ml
UPDATE public.products
  SET vetspire_product_id = 646564,
      vetspire_product_name = 'Prednisolone Solu 15 mg/ 5 ml'
  WHERE name ILIKE '%prednisolone%'
  AND name ILIKE '%15 mg%';

-- Proparacaine 0.5% Opthalmic Solu
UPDATE public.products
  SET vetspire_product_id = 646590,
      vetspire_product_name = 'Proparacaine 0.5% Opthalmic Solu (15 ml)'
  WHERE name ILIKE '%proparacaine%'
  AND name ILIKE '%0.5%%';

-- Proviable Fiber / tsp
UPDATE public.products
  SET vetspire_product_id = 2511275,
      vetspire_product_name = 'Proviable Fiber / tsp '
  WHERE name ILIKE '%proviable%'
  AND name ILIKE '%fiber%';

-- Proviable Paste Kit
UPDATE public.products
  SET vetspire_product_id = 646573,
      vetspire_product_name = 'Proviable Paste Kit  (Cat/Small Dog) '
  WHERE name ILIKE '%proviable%'
  AND name ILIKE '%paste%';

-- Proviable Paste Kit
UPDATE public.products
  SET vetspire_product_id = 646573,
      vetspire_product_name = 'Proviable Paste Kit  (Cat/Small Dog) '
  WHERE name ILIKE '%proviable%'
  AND name ILIKE '%paste%';

-- PureVax 3 Feline RCP Vaccine
UPDATE public.products
  SET vetspire_product_id = 871643,
      vetspire_product_name = 'PureVax 3 Feline RCP Vaccine'
  WHERE name ILIKE '%purevax%'
  AND name ILIKE '%feline%'
  AND name ILIKE '%3%';

-- PureVax Feline Rabies Vaccine - 1 Year
UPDATE public.products
  SET vetspire_product_id = 646383,
      vetspire_product_name = 'PureVax Feline Rabies Vaccine - 1 Year'
  WHERE name ILIKE '%purevax%'
  AND name ILIKE '%feline%';

-- PureVax Feline Rabies Vaccine - 3 Year
UPDATE public.products
  SET vetspire_product_id = 646384,
      vetspire_product_name = 'PureVax Feline Rabies Vaccine - 3 Year'
  WHERE name ILIKE '%purevax%'
  AND name ILIKE '%feline%'
  AND name ILIKE '%3%';

-- PureVax Recombinant FeLV Vaccine
UPDATE public.products
  SET vetspire_product_id = 646385,
      vetspire_product_name = 'PureVax Recombinant FeLV Vaccine'
  WHERE name ILIKE '%purevax%'
  AND name ILIKE '%recombinant%';

-- Revolution PLUS Topical 11.1 to 22 lbs
UPDATE public.products
  SET vetspire_product_id = 646676,
      vetspire_product_name = 'Revolution PLUS Topical 11.1 to 22 lbs'
  WHERE name ILIKE '%revolution%'
  AND name ILIKE '%plus%'
  AND name ILIKE '%11%';

-- Revolution PLUS Topical 2.8 to 5.5 lbs
UPDATE public.products
  SET vetspire_product_id = 646674,
      vetspire_product_name = 'Revolution PLUS Topical 2.8 to 5.5 lbs'
  WHERE name ILIKE '%revolution%'
  AND name ILIKE '%plus%'
  AND name ILIKE '%2%';

-- Revolution PLUS Topical 5.6 to 11 lbs
UPDATE public.products
  SET vetspire_product_id = 646675,
      vetspire_product_name = 'Revolution PLUS Topical 5.6 to 11 lbs'
  WHERE name ILIKE '%revolution%'
  AND name ILIKE '%plus%'
  AND name ILIKE '%5%';

-- Revolution Puppies & Kittens < 5 lbs
UPDATE public.products
  SET vetspire_product_id = 886430,
      vetspire_product_name = 'Revolution Puppies & Kittens < 5 lbs'
  WHERE name ILIKE '%revolution%'
  AND name ILIKE '%puppies%'
  AND name ILIKE '%5%';

-- Robenacoxib 6 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646576,
      vetspire_product_name = 'Robenacoxib 6 mg tablets (3/box)'
  WHERE name ILIKE '%robenacoxib%'
  AND name ILIKE '%6 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Royal Canin Feline SO
UPDATE public.products
  SET vetspire_product_id = 646680,
      vetspire_product_name = 'Royal Canin Feline SO (5.1 oz)'
  WHERE name ILIKE '%royal%'
  AND name ILIKE '%canin%'
  AND name ILIKE '%5%';

-- SNAP 4DX Plus Test
UPDATE public.products
  SET vetspire_product_id = 628229,
      vetspire_product_name = 'SNAP 4DX Plus Test'
  WHERE name ILIKE '%snap%'
  AND name ILIKE '%plus%';

-- SNAP Feline Triple Test
UPDATE public.products
  SET vetspire_product_id = 628234,
      vetspire_product_name = 'SNAP Feline Triple Test'
  WHERE name ILIKE '%snap%'
  AND name ILIKE '%feline%';

-- SNAP Feline proBNP Test
UPDATE public.products
  SET vetspire_product_id = 628237,
      vetspire_product_name = 'SNAP Feline proBNP Test'
  WHERE name ILIKE '%snap%'
  AND name ILIKE '%feline%';

-- SNAP Parvo Test
UPDATE public.products
  SET vetspire_product_id = 628233,
      vetspire_product_name = 'SNAP Parvo Test'
  WHERE name ILIKE '%snap%'
  AND name ILIKE '%parvo%';

-- Solensia
UPDATE public.products
  SET vetspire_product_id = 873304,
      vetspire_product_name = 'Solensia '
  WHERE name ILIKE '%solensia%';

-- Sucralfate 1 gm tablets
UPDATE public.products
  SET vetspire_product_id = 1743750,
      vetspire_product_name = 'Sucralfate 1 gm tablets'
  WHERE name ILIKE '%sucralfate%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Tobramycin 0.3% Ophthalmic Solu
UPDATE public.products
  SET vetspire_product_id = 646597,
      vetspire_product_name = 'Tobramycin 0.3% Ophthalmic Solu (5 ml)'
  WHERE name ILIKE '%tobramycin%'
  AND name ILIKE '%0.3%%';

-- Trazodone 100 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646580,
      vetspire_product_name = 'Trazodone 100 mg tablets'
  WHERE name ILIKE '%trazodone%'
  AND name ILIKE '%100 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Trazodone 50 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646581,
      vetspire_product_name = 'Trazodone 50 mg tablets'
  WHERE name ILIKE '%trazodone%'
  AND name ILIKE '%50 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- TrizEDTA Aqueous Otic Flush
UPDATE public.products
  SET vetspire_product_id = 1069603,
      vetspire_product_name = 'TrizEDTA Aqueous Otic Flush (4 oz)'
  WHERE name ILIKE '%trizedta%'
  AND name ILIKE '%aqueous%'
  AND name ILIKE '%4%';

-- TrizULTRA + KETO Otic Flush
UPDATE public.products
  SET vetspire_product_id = 646608,
      vetspire_product_name = 'TrizULTRA + KETO Otic Flush (12 oz)'
  WHERE name ILIKE '%trizultra%'
  AND name ILIKE '%keto%'
  AND name ILIKE '%12%';

-- Vanguard Bordetella Vaccine Oral SF
UPDATE public.products
  SET vetspire_product_id = 646376,
      vetspire_product_name = 'Vanguard Bordetella Vaccine Oral SF'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%bordetella%';

-- Vanguard CIV Vaccine
UPDATE public.products
  SET vetspire_product_id = 646377,
      vetspire_product_name = 'Vanguard CIV Vaccine (H3N2 & H3N8)'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%vaccine%';

-- Vanguard DAPP + L4 Vaccine
UPDATE public.products
  SET vetspire_product_id = 646379,
      vetspire_product_name = 'Vanguard DAPP + L4 Vaccine'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%dapp%';

-- Vanguard DAPP Vaccine
UPDATE public.products
  SET vetspire_product_id = 646380,
      vetspire_product_name = 'Vanguard DAPP Vaccine'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%dapp%';

-- Vanguard L4 Lepto Vaccine
UPDATE public.products
  SET vetspire_product_id = 646381,
      vetspire_product_name = 'Vanguard L4 Lepto Vaccine'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%lepto%';

-- Vanguard Rabies Vaccine - 1 Year
UPDATE public.products
  SET vetspire_product_id = 646374,
      vetspire_product_name = 'Vanguard Rabies Vaccine - 1 Year'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%rabies%';

-- Vanguard Rabies Vaccine - 3 Year
UPDATE public.products
  SET vetspire_product_id = 646373,
      vetspire_product_name = 'Vanguard Rabies Vaccine - 3 Year'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%rabies%'
  AND name ILIKE '%3%';

-- Vanguard crLyme Vaccine
UPDATE public.products
  SET vetspire_product_id = 646378,
      vetspire_product_name = 'Vanguard crLyme Vaccine'
  WHERE name ILIKE '%vanguard%'
  AND name ILIKE '%crlyme%';

-- Veraflox Susp 25 mg/ml
UPDATE public.products
  SET vetspire_product_id = 646584,
      vetspire_product_name = 'Veraflox Susp 25 mg/ml (15 ml bottle)'
  WHERE name ILIKE '%veraflox%'
  AND name ILIKE '%25 mg/ml%';

-- Viralys Powder
UPDATE public.products
  SET vetspire_product_id = 837585,
      vetspire_product_name = 'Viralys Powder '
  WHERE name ILIKE '%viralys%'
  AND name ILIKE '%powder%';

-- Vitamin K-1 50 mg tablets
UPDATE public.products
  SET vetspire_product_id = 646585,
      vetspire_product_name = 'Vitamin K-1 50 mg tablets'
  WHERE name ILIKE '%vitamin%'
  AND name ILIKE '%50 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Yunnan Baiyao
UPDATE public.products
  SET vetspire_product_id = 646587,
      vetspire_product_name = 'Yunnan Baiyao (16/box)'
  WHERE name ILIKE '%yunnan%'
  AND name ILIKE '%baiyao%'
  AND name ILIKE '%16%';

-- Zymox Otic with 1% Hydrocortisone
UPDATE public.products
  SET vetspire_product_id = 1382123,
      vetspire_product_name = 'Zymox Otic with 1% Hydrocortisone (1.25 oz)'
  WHERE name ILIKE '%zymox%'
  AND name ILIKE '%1%%';

-- Capstar Tablet 11.4 mg
UPDATE public.products
  SET vetspire_product_id = 646662,
      vetspire_product_name = 'Capstar Tablet 11.4 mg (Cats  and Small  Dogs 2 to 25 lbs)'
  WHERE name ILIKE '%capstar%'
  AND name ILIKE '%11.4 mg%'
  AND (name ILIKE '%tablet%' OR name ILIKE '% tab%' OR name ILIKE '%caplet%')
  AND name NOT ILIKE '%inj%' AND name NOT ILIKE '%mg/ml%';

-- Drontal
UPDATE public.products
  SET vetspire_product_id = 646510,
      vetspire_product_name = 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Puppies & Small Dogs'
  WHERE name ILIKE '%revolution%'
  AND name ILIKE '%puppies%'
  AND name ILIKE '%5%';

-- Metamucil
UPDATE public.products
  SET vetspire_product_id = 1743626,
      vetspire_product_name = 'Metamucil (Psyllium Husk Fiber) / tsp'
  WHERE name ILIKE '%metamucil%'
  AND name ILIKE '%psyllium%';

-- Omnipaque
UPDATE public.products
  SET vetspire_product_id = 646648,
      vetspire_product_name = 'Omnipaque (Iohexol) Inj 350 mg/ml'
  WHERE name ILIKE '%omnipaque%'
  AND name ILIKE '%350 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Pyrantel Pamoate
UPDATE public.products
  SET vetspire_product_id = 886430,
      vetspire_product_name = 'Pyrantel Pamoate (50 mg/ml)'
  WHERE name ILIKE '%pyrantel%'
  AND name ILIKE '%50 mg/ml%';

-- Solovecin
UPDATE public.products
  SET vetspire_product_id = 2148179,
      vetspire_product_name = 'Solovecin (Cefovecin Sodium) Inj 80 mg/ml'
  WHERE name ILIKE '%solovecin%'
  AND name ILIKE '%80 mg/ml%'
  AND (name ILIKE '%inj%' OR name ILIKE '%mg/ml%' OR name ILIKE '%solution%')
  AND name NOT ILIKE '%tablet%' AND name NOT ILIKE '% tab %';

-- Terramycin
UPDATE public.products
  SET vetspire_product_id = 646595,
      vetspire_product_name = 'Terramycin (Oxytetracycline Hydrochloride) Opthalmic Ointment  (3.5 gm)'
  WHERE name ILIKE '%terramycin%'
  AND name ILIKE '%oxytetracycline%'
  AND name ILIKE '%3%';

-- ToxiBan
UPDATE public.products
  SET vetspire_product_id = 646579,
      vetspire_product_name = 'ToxiBan (without Sorbitol)'
  WHERE name ILIKE '%toxiban%'
  AND name ILIKE '%without%';

-- STEP 3: Verification
SELECT
  COUNT(*) FILTER (WHERE vetspire_product_id IS NOT NULL) AS mapped,
  COUNT(*) FILTER (WHERE vetspire_product_id IS NULL) AS unmapped,
  COUNT(*) AS total
FROM public.products;
-- Manual patches: Drontal variants + Furosemide Syrup
-- Drontal for Cats and Kittens
UPDATE public.products
  SET vetspire_product_id = 646509,
      vetspire_product_name = 'Drontal (Praziquantel/Pyrantel Pamoate) for Cats and Kittens'
  WHERE name ILIKE '%drontal%'
    AND name ILIKE '%praziquantel%'
    AND (name ILIKE '%cat%' OR name ILIKE '%kitten%');

-- Drontal PLUS for Large Dogs
UPDATE public.products
  SET vetspire_product_id = 667665,
      vetspire_product_name = 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Large Dogs'
  WHERE name ILIKE '%drontal%'
    AND name ILIKE '%large%';

-- Drontal PLUS for Medium Dogs
UPDATE public.products
  SET vetspire_product_id = 667664,
      vetspire_product_name = 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Medium Dogs'
  WHERE name ILIKE '%drontal%'
    AND name ILIKE '%medium%';

-- Drontal PLUS for Puppies & Small Dogs
UPDATE public.products
  SET vetspire_product_id = 646510,
      vetspire_product_name = 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Puppies & Small Dogs'
  WHERE name ILIKE '%drontal%'
    AND (name ILIKE '%puppy%' OR name ILIKE '%puppies%' OR name ILIKE '%small%');

-- Furosemide Syrup 1%
UPDATE public.products
  SET vetspire_product_id = 667659,
      vetspire_product_name = 'Furosemide Syrup 1% (10 mg/ml)'
  WHERE name ILIKE '%furosemide%'
    AND name ILIKE '%syrup%';

