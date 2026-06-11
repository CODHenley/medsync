-- Add practice types to organizations (multi-select, stored as array)
ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS practice_types TEXT[] DEFAULT '{}';

-- Add practice type to locations (single type per location)
ALTER TABLE public.locations
  ADD COLUMN IF NOT EXISTS practice_type TEXT;

-- Index for filtering orgs/locations by practice type
CREATE INDEX IF NOT EXISTS idx_organizations_practice_types ON public.organizations USING GIN (practice_types);
CREATE INDEX IF NOT EXISTS idx_locations_practice_type ON public.locations (practice_type);

-- Seed Scout with their known type
UPDATE public.organizations
  SET practice_types = ARRAY['urgent_care']
  WHERE id = 'ce27c4f4-7352-4128-86ff-b1891b50933c'
  AND (practice_types IS NULL OR practice_types = '{}');
