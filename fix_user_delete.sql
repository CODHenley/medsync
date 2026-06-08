-- Fix 1: Allow deletes on the users table (missing RLS policy)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_all" ON public.users;
CREATE POLICY "users_all" ON public.users FOR ALL USING (true) WITH CHECK (true);

-- Fix 2: Remove Tripp's existing record so you can re-add him with his real email
DELETE FROM public.users WHERE email ILIKE '%tripp%' OR email ILIKE '%welge%' OR full_name ILIKE '%trip%';

-- Fix 3: Remove the auth record so his email is free to re-register
DELETE FROM auth.users WHERE email ILIKE '%tripp%' OR email ILIKE '%welge%';

-- Verify he's gone
SELECT id, full_name, email, role FROM public.users ORDER BY created_at DESC LIMIT 10;
