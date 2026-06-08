-- Tripp already exists in public.users — just update his record to ensure correct role/name
UPDATE public.users
SET
  full_name  = 'Tripp Welge',
  role       = 'admin',
  is_active  = true,
  email      = 'tripp@thurlowvet.com'
WHERE id = (SELECT id FROM auth.users WHERE email = 'tripp@thurlowvet.com');

-- Verify
SELECT id, full_name, email, role, is_active FROM public.users WHERE email = 'tripp@thurlowvet.com';
