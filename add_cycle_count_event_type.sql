-- MedSync — Add 'count' to activity_log event_type check constraint
-- Run once in: Supabase → SQL Editor → New Query → Paste → Run

-- 1. Drop the existing check constraint (name may vary — find it first)
ALTER TABLE activity_log
  DROP CONSTRAINT IF EXISTS activity_log_event_type_check;

-- 2. Re-add with 'count' included
ALTER TABLE activity_log
  ADD CONSTRAINT activity_log_event_type_check
  CHECK (event_type IN ('order', 'receive', 'goods', 'user', 'count'));
