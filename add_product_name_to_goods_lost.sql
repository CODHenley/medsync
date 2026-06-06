-- MedSync — Add product_name to goods_lost for Vetspire sync
-- Run once in: Supabase → SQL Editor → New Query → Paste → Run

ALTER TABLE goods_lost
  ADD COLUMN IF NOT EXISTS product_name TEXT;
