-- Update dispensing_unit and package_size from Scout Product List (Demand Forecast)
-- Source: Demand_Forecasting_Spreadsheet_2026_v4.xlsx → Product List sheet
-- Columns: product_name | purchase_unit | package_size | dispensing_unit

UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Albon (Sulfadimethoxine) 250 mg tablets';
UPDATE public.products SET dispensing_unit='can', purchase_unit='can', package_size=1
  WHERE name ILIKE 'Albuterol HFA 90 mcg';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Alfaxalone Inj 10 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=473
  WHERE name ILIKE 'Aluminum Hydroxide 64 mg/ml solution';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=90
  WHERE name ILIKE 'Amlodipine 2.5 mg tablets';
UPDATE public.products SET dispensing_unit='vials', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Amp+Sulbactam Inj 30 mg/ml (1.5 g vial)';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Animax Ointment (15 ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Apomorphine HCl 3 mg/ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=250
  WHERE name ILIKE 'Apoquel 16 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=250
  WHERE name ILIKE 'Apoquel 3.6 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=250
  WHERE name ILIKE 'Apoquel 5.4 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Atipamezole HCl  Inj 5 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Atropine Inj 0.54 mg/ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Aural Hematoma - Teat Cannula ';
UPDATE public.products SET dispensing_unit='bottles', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Baytril Otic (15 ml)';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'BNP Opthalmic Ointment (3.5 gm)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Buprenorphine  Inj 0.3 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=50
  WHERE name ILIKE 'Butorphanol Inj 10 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Calcium Gluconate 10% Inj (100 mg/ml)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='pack', package_size=6
  WHERE name ILIKE 'Capstar Tablet 11.4 mg (Cats  and Small  Dogs 2 to 25 lbs)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=180
  WHERE name ILIKE 'Carprofen 100 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=180
  WHERE name ILIKE 'Carprofen 25 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=180
  WHERE name ILIKE 'Carprofen 75 mg tablets';
UPDATE public.products SET dispensing_unit='rolls', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Cast - Vetcast 2in';
UPDATE public.products SET dispensing_unit='rolls', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Cast - Vetcast 3in';
UPDATE public.products SET dispensing_unit='rolls', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Cast - Vetcast 4in';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Alkaline Aminotransferase (ALT)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Alkaline Phosphatase (ALP)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Ammonia (NH3)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Blood Urea Nitrogen (BUN)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Chem 10';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Chem 17';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Catalyst Cortisol';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Creatinine (CREA)';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Catalyst Fructosamine (FRU)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Inorganic Phosphate (PHOS)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Lactate (LAC)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Lytes 4';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst NSAID 6';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Pancreatic Lipase  (PL)';
UPDATE public.products SET dispensing_unit='clips', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Total Bilirubin (TBILI)';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Catalyst Total T4 (TT4)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Cefpodoxime 200 mg tablets';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Cephalexin 250 mg capsules';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Cephalexin 500 mg capsules';
UPDATE public.products SET dispensing_unit='tubes', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Claro Otic (1 ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=15
  WHERE name ILIKE 'Clavacillin  Susp 62.5 mg/ml (15 ml bottle)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=210
  WHERE name ILIKE 'Clavacillin 125 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=210
  WHERE name ILIKE 'Clavacillin 250 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=210
  WHERE name ILIKE 'Clavacillin 375 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=210
  WHERE name ILIKE 'Clavacillin 62.5 mg tablets';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Clindamycin 150 mg capsules';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=20
  WHERE name ILIKE 'Clindamycin Susp 25 mg/ml (20 ml bottle)';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Coag Dx Citrate Activated Partial Thromboplastin Time (aPTT)';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=10
  WHERE name ILIKE 'Coag Dx Citrate Prothrombin Time (PT)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Convenia (Cefovecin Sodium) Inj 80 mg/ml';
UPDATE public.products SET dispensing_unit='vial', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Cytopoint 10 mg (1 ml vial)';
UPDATE public.products SET dispensing_unit='vial', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Cytopoint 20 mg (1 ml vial)';
UPDATE public.products SET dispensing_unit='vial', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Cytopoint 30 mg (1 ml vial)';
UPDATE public.products SET dispensing_unit='vial', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Cytopoint 40 mg (1 ml vial)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=1
  WHERE name ILIKE 'Dexamethasone-SP Inj 4 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Dexmedetomidine Inj 0.5 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Dextrose Solu Inj 50%';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Diphenhydramine 25 mg capsules';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Diphenhydramine 50 mg capsules';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Diphenhydramine Inj 50 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=120
  WHERE name ILIKE 'Diphenhydramine Syrup 12.5 mg/5 ml  ';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Dorzolamide Timolol 2-0.5% Solu (10 ml)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Douxo S3 PYO Mousse (5.1 oz)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Douxo S3 PYO Shampoo (6.7 oz)';
UPDATE public.products SET dispensing_unit='wipes', purchase_unit='pack', package_size=30
  WHERE name ILIKE 'Douxo S3 PYO Wipes (30 ct)';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Doxycycline 100 mg capsules';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Doxycycline 100 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=120
  WHERE name ILIKE 'Doxycycline Solu 100 mg/ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Drain - Continuous Suction Bulb 100 ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Drain - Jackson Pratt 10fr';
UPDATE public.products SET dispensing_unit='each', purchase_unit='pack', package_size=10
  WHERE name ILIKE 'Drain - Penrose 1/4 in x 18 in';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Drontal (Praziquantel/Pyrantel Pamoate) for Cats and Kittens ';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30
  WHERE name ILIKE 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Large Dogs ';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Medium Dogs ';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Drontal (Praziquantel/Pyrantel Pamoate/Febantel) PLUS for Puppies & Small Dogs';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 10 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 12 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 15 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 20 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 25 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 30 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'E-Collar - 7.5 cm';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=15
  WHERE name ILIKE 'Elura 20 mg/ml (15 ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=120
  WHERE name ILIKE 'Endosorb Susp';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Endosorb Tablets';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 10 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 10.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 11.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 3.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 3.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 4.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 4.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 5.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 5.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 6.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 6.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 7.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 7.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 8.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 8.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 9.0 mm Cuffed';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Endotracheal Tube - 9.5 mm Cuffed';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Enrofloxacin 136 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=15
  WHERE name ILIKE 'Entyce 30 mg/ml (15 ml)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Epi-Otic Advanced Ear Cleanser (8 oz)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=50
  WHERE name ILIKE 'Epinephrine Inj 1 mg/ml';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Erythromycin 0.5% Ophthalmic Ointment (3.5 gm)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Euthasol';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'EZ Soft Collar - Small ';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'EZ Soft Collar - XS';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30
  WHERE name ILIKE 'Famotidine 10 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Famotidine Inj 10 mg/mL';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=1000
  WHERE name ILIKE 'Fenbendazole Susp 100 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=5
  WHERE name ILIKE 'Flumazenil Inj  0.1 mg/ml';
UPDATE public.products SET dispensing_unit='strips', purchase_unit='box', package_size=100
  WHERE name ILIKE 'Fluorescein I-Glo Test Strip';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Furosemide 12.5 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=50
  WHERE name ILIKE 'Furosemide Inj 50 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=60
  WHERE name ILIKE 'Furosemide Syrup 1% (10 mg/ml)';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Gabapentin 100 mg capsules';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='pack', package_size=30
  WHERE name ILIKE 'Gabapentin 100 mg QuadTabs';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Gabapentin 300 mg capsules';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=480
  WHERE name ILIKE 'Gabapentin Solu 100 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='jug', package_size=3785
  WHERE name ILIKE 'Glycerin 99% U.S.P.  (1 Gallon)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=24
  WHERE name ILIKE 'Hill''s c/d Feline Urinary Care (5.5 oz)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=12
  WHERE name ILIKE 'Hill''s Canine Gastrointestinal Biome Chicken and Vegetable Stew (12.5oz)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=12
  WHERE name ILIKE 'Hill''s Feline Gastrointestinal Biome (2.9 oz)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=12
  WHERE name ILIKE 'Hill''s i/d Canine Chicken and Vegetable Stew (12.5 oz)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=12
  WHERE name ILIKE 'Hill''s i/d Canine Low Fat Stew (12.5 oz)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=24
  WHERE name ILIKE 'Hill''s i/d Feline (5.5 oz)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=473
  WHERE name ILIKE 'Hydrocodone 5 mg /Homatropine 1.5 mg Solu / 5ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Hydromorphone Inj 2 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bag', package_size=1000
  WHERE name ILIKE 'Hypertonic Saline Inj 7.2%';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Ketamine HCl Inj 100 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=946
  WHERE name ILIKE 'Lactulose Solu 10 g/15 ml (32 oz)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Latanoprost Ophthalmic Solu 0.005% (2.5 ml)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=120
  WHERE name ILIKE 'Levetiracetam 250 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=120
  WHERE name ILIKE 'Levetiracetam 750 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=473
  WHERE name ILIKE 'Levetiracetam Solu 100 mg/ml (16 oz)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Lidocaine HCl 2%  Oral Solu (20 mg/ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Lidocaine HCl 2% Inj (20 mg/ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Mannitol 20% Inj (200 mg/ml)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='pack', package_size=4
  WHERE name ILIKE 'Maropitant 16 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='pack', package_size=4
  WHERE name ILIKE 'Maropitant 24 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='pack', package_size=4
  WHERE name ILIKE 'Maropitant 60 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Maropitant Inj 10 mg/ml';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=15
  WHERE name ILIKE 'Meloxicam Susp 0.5 mg/ml';
UPDATE public.products SET dispensing_unit='canister', purchase_unit='canister', package_size=1
  WHERE name ILIKE 'Metamucil (Psyllium Husk Fiber) / tsp';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Methadone Inj 10 mg/ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Methimazole 5 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Methocarbamol 500 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Metronidazole 250 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=500
  WHERE name ILIKE 'Metronidazole 500 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=460
  WHERE name ILIKE 'Metronidazole Benzoate Sus 100 mg/ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Metronidazole Tiny Tabs 50 mg  tablets';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Microchip';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Midazolam Inj 5 mg/ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30
  WHERE name ILIKE 'Mirtazapine 7.5mg tablets';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Mirtazapine Transdermal Ointment 5 gm';
UPDATE public.products SET dispensing_unit='bottles', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Mometamax Susp (15 gm)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Naloxone Inj 0.4 mg/ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Nasogastric Tube - 10fr x 90 cm';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Nasogastric Tube - 5fr x 55 cm MILA';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Nasogastric Tube - 6fr x 55 cm MILA';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Nasogastric Tube - 8fr x 90 cm MILA';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Nitro-Bid Ointment 2%';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'No Flap Ear Wrap - Large';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'No Flap Ear Wrap - Medium';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'No Flap Ear Wrap - Small';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'NPD Ophthalmic Ointment (3.5g)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'NPD Ophthalmic Susp (5 ml)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Ofloxacin 0.3% Ophthalmic Solu (5 ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Omnipaque (Iohexol) Inj 350 mg/ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30
  WHERE name ILIKE 'Ondansetron 4 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=30
  WHERE name ILIKE 'Ondansetron 8 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=20
  WHERE name ILIKE 'Ondansetron Inj 2 mg/ml';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Optixcare PLUS Eye Lube (20 gm)';
UPDATE public.products SET dispensing_unit='packets', purchase_unit='box', package_size=3
  WHERE name ILIKE 'Panacur C Canine 1 g (3/box)';
UPDATE public.products SET dispensing_unit='packets', purchase_unit='box', package_size=3
  WHERE name ILIKE 'Panacur C Canine 2 g  (3/box)';
UPDATE public.products SET dispensing_unit='packets', purchase_unit='box', package_size=3
  WHERE name ILIKE 'Panacur C Canine 4 g (3/box)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Pimobendan 2.5 mg tablets';
UPDATE public.products SET dispensing_unit='bottles', purchase_unit='box', package_size=12
  WHERE name ILIKE 'Posatex Susp (15 gm)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Prazosin Tiny Tabs 0.5 mg';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Prednisolone  Acetate 1% Opthalmic Susp (5 ml)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=1000
  WHERE name ILIKE 'Prednisolone 5 mg tablets';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=237
  WHERE name ILIKE 'Prednisolone Solu 15 mg/ 5 ml';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'PredniSONE 10 mg tablets';
UPDATE public.products SET dispensing_unit='kit', purchase_unit='kit', package_size=1
  WHERE name ILIKE 'Procyte Dx Reagent Kit';
UPDATE public.products SET dispensing_unit='kit', purchase_unit='kit', package_size=1
  WHERE name ILIKE 'Procyte Quality Control e-CHECK';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Proparacaine 0.5% Opthalmic Solu (15 ml)';
UPDATE public.products SET dispensing_unit='kit', purchase_unit='kit', package_size=1
  WHERE name ILIKE 'Proviable Paste Kit  (Cat/Small Dog) ';
UPDATE public.products SET dispensing_unit='kit', purchase_unit='kit', package_size=1
  WHERE name ILIKE 'Proviable Paste Kit (Medium/Large Dog)';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'PureVax 3 Feline RCP Vaccine';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'PureVax Feline Rabies Vaccine - 1 Year';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'PureVax Feline Rabies Vaccine - 3 Year';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'PureVax Recombinant FeLV Vaccine';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=473
  WHERE name ILIKE 'Pyrantel Pamoate (50 mg/ml)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Rabies Tag - 1 year';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Red Rubber - 10fr x 16in';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Red Rubber - 3.5fr x 16in';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Red Rubber - 5fr x 16in';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Red Rubber - 8fr x 22in';
UPDATE public.products SET dispensing_unit='tubes', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Revolution PLUS Topical 11.1 to 22 lbs';
UPDATE public.products SET dispensing_unit='tubes', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Revolution PLUS Topical 2.8 to 5.5 lbs';
UPDATE public.products SET dispensing_unit='tubes', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Revolution PLUS Topical 5.6 to 11 lbs';
UPDATE public.products SET dispensing_unit='tubes', purchase_unit='box', package_size=3
  WHERE name ILIKE 'Revolution Puppies & Kittens < 5 lbs';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='box', package_size=3
  WHERE name ILIKE 'Robenacoxib 6 mg tablets (3/box)';
UPDATE public.products SET dispensing_unit='cans', purchase_unit='case', package_size=24
  WHERE name ILIKE 'Royal Canin Feline SO (5.1 oz)';
UPDATE public.products SET dispensing_unit='strips', purchase_unit='box', package_size=50
  WHERE name ILIKE 'Schirmer Tear Test';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=30
  WHERE name ILIKE 'SNAP 4DX Plus Test';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=5
  WHERE name ILIKE 'SNAP Feline proBNP Test';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=15
  WHERE name ILIKE 'SNAP Feline Triple Test';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=10
  WHERE name ILIKE 'SNAP fPL Test';
UPDATE public.products SET dispensing_unit='tests', purchase_unit='box', package_size=5
  WHERE name ILIKE 'SNAP Parvo Test';
UPDATE public.products SET dispensing_unit='vials', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Solensia ';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Solovecin (Cefovecin Sodium) Injectable 80mg/ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Large LFL/RFL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Large LHL/RHL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Medium LFL/RFL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Medium LHL/RHL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Small LFL/RFL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Quick Splint (Small LHL/RHL)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Spoon Splint (Large)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Spoon Splint (Medium)';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Splint - Spoon Splint (Small)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Sucralfate 1 gm tablets';
UPDATE public.products SET dispensing_unit='tube', purchase_unit='tube', package_size=1
  WHERE name ILIKE 'Terramycin (Oxytetracycline Hydrochloride) Opthalmic Ointment  (3.5 gm)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Tobramycin 0.3% Ophthalmic Solu (5 ml)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='bottle', package_size=240
  WHERE name ILIKE 'ToxiBan (without Sorbitol)';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Trazodone 100 mg tablets';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=100
  WHERE name ILIKE 'Trazodone 50 mg tablets';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'TrizEDTA Aqueous Otic Flush (4 oz)';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'TrizULTRA + KETO Otic Flush (12 oz)';
UPDATE public.products SET dispensing_unit='box', purchase_unit='box', package_size=1
  WHERE name ILIKE 'UA Strip';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urinary Catheter - Foley 10fr x 90 cm w/ stylet';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urinary Catheter - Foley 6fr x 60 cm w/ stylet';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urinary Catheter - Foley 8fr x 60 cm w/ stylet';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urinary Catheter - Slippery Sam Tomcat 3.5fr x 5in Closed End';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urinary Catheter - Slippery Sam Tomcat 3.5fr x 6in Closed End';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urine Collection Kit 1000 ml';
UPDATE public.products SET dispensing_unit='each', purchase_unit='each', package_size=1
  WHERE name ILIKE 'Urine Drug Screen';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard Bordetella Oral SF';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard CIV (H3N2 & H3N8)';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard crLyme Vaccine';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard DAPP + L4 Vaccine';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard DAPP Vaccine';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=25
  WHERE name ILIKE 'Vanguard L4 Lepto Vaccine';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=50
  WHERE name ILIKE 'Vanguard Rabies Vaccine - 1 Year';
UPDATE public.products SET dispensing_unit='doses', purchase_unit='tray', package_size=50
  WHERE name ILIKE 'Vanguard Rabies Vaccine - 3 Year';
UPDATE public.products SET dispensing_unit='bottles', purchase_unit='box', package_size=6
  WHERE name ILIKE 'Veraflox Susp 25 mg/ml (15 ml bottle)';
UPDATE public.products SET dispensing_unit='jar', purchase_unit='jar', package_size=1
  WHERE name ILIKE 'Viralys Powder ';
UPDATE public.products SET dispensing_unit='tablets', purchase_unit='bottle', package_size=50
  WHERE name ILIKE 'Vitamin K-1 50 mg tablets';
UPDATE public.products SET dispensing_unit='capsules', purchase_unit='box', package_size=16
  WHERE name ILIKE 'Yunnan Baiyao (16/box)';
UPDATE public.products SET dispensing_unit='mL', purchase_unit='vial', package_size=10
  WHERE name ILIKE 'Zenalpha 0.5 mg/ml';
UPDATE public.products SET dispensing_unit='bottle', purchase_unit='bottle', package_size=1
  WHERE name ILIKE 'Zymox Otic with 1% Hydrocortisone 1.25oz bottle';

-- Verify
SELECT name, purchase_unit, package_size, dispensing_unit FROM public.products
WHERE dispensing_unit IS NOT NULL ORDER BY name LIMIT 30;