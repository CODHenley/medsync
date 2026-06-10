-- Remove all auto-flagged queued PO items that don't have a Vetspire min/max set.
-- These were incorrectly auto-added before the Vetspire-only filter was in place.
-- Safe to run — only deletes 'queued' + 'auto_flagged' items, never submitted POs.

DELETE FROM public.po_items
WHERE status = 'queued'
  AND auto_flagged = true
  AND (
    product_id IS NULL
    OR product_id NOT IN (
      SELECT id FROM public.products WHERE qty_min IS NOT NULL
    )
  );

-- Also clear any queued items older than 14 days (they're from past weeks anyway)
DELETE FROM public.po_items
WHERE status = 'queued'
  AND auto_flagged = true
  AND added_at < NOW() - INTERVAL '14 days';
