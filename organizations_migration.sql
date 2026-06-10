-- ============================================================
-- organizations_migration.sql
-- Multi-tenant organization support + location limits
-- ============================================================

-- STEP 1: organizations — one row per paying customer
CREATE TABLE IF NOT EXISTS public.organizations (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name             TEXT NOT NULL,
  tier             TEXT NOT NULL DEFAULT 'solo',
    -- solo | small_group | mid_group | large_group | enterprise | internal
  location_limit   INT NOT NULL DEFAULT 1,
    -- 1 / 3 / 6 / 12 / 999 (enterprise/internal = effectively unlimited)
  status           TEXT NOT NULL DEFAULT 'active',
    -- active | suspended | churned
  contact_name     TEXT,
  contact_email    TEXT,
  notes            TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- STEP 2: Add organization_id to locations (nullable — null = legacy/Scout)
ALTER TABLE public.locations
  ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;

-- STEP 3: Add organization_id to users (nullable — null = legacy/Scout)
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;

-- STEP 4: Indexes
CREATE INDEX IF NOT EXISTS idx_orgs_status          ON public.organizations (status);
CREATE INDEX IF NOT EXISTS idx_locations_org         ON public.locations (organization_id);
CREATE INDEX IF NOT EXISTS idx_users_org             ON public.users (organization_id);

-- STEP 5: RLS — anon read/write (matches existing pattern)
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_all_organizations" ON public.organizations;
CREATE POLICY "anon_all_organizations"
  ON public.organizations FOR ALL TO anon USING (true) WITH CHECK (true);

-- STEP 6: Seed — insert Scout as the internal/legacy org
-- Run this AFTER the table exists. Update Scout location + user rows to point here if desired.
INSERT INTO public.organizations (name, tier, location_limit, status, contact_name, contact_email, notes)
VALUES (
  'Scout Veterinary Urgent Care',
  'internal',
  999,
  'active',
  'Megan Henley',
  'mhenley@scoutcare.com',
  'Founding customer — perpetual preferred pricing. Legacy org; existing locations/users may have null organization_id.'
)
ON CONFLICT DO NOTHING;

-- STEP 7: Seed — MedSync internal superadmin user
-- After running this migration, create a user in Supabase Auth with email admin@medsync.vet,
-- then INSERT that user's auth UUID here:
--
-- INSERT INTO public.users (id, email, full_name, role, organization_id)
-- VALUES ('<auth-uuid>', 'admin@medsync.vet', 'MedSync Admin', 'medsync_superadmin', NULL)
-- ON CONFLICT (id) DO UPDATE SET role = 'medsync_superadmin';

-- STEP 8: Verify
SELECT 'organizations' AS table_name, COUNT(*) FROM public.organizations
UNION ALL
SELECT 'locations with org_id', COUNT(*) FROM public.locations WHERE organization_id IS NOT NULL
UNION ALL
SELECT 'users with org_id', COUNT(*) FROM public.users WHERE organization_id IS NOT NULL;
