-- MedSync Demo Location Cleanup
-- Removes placeholder locations added for early testing.
-- Run BEFORE the Tripp pitch.
-- SAFE: only deletes by exact name match — real Scout locations are untouched.

-- Preview first (run this SELECT to confirm what will be deleted):
SELECT id, name FROM locations
WHERE name IN ('Naperville', 'Aurora', 'Schaumburg');

-- Then run the DELETE:
DELETE FROM locations
WHERE name IN ('Naperville', 'Aurora', 'Schaumburg');
