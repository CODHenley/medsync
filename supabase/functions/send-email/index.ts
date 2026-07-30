const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

// Accepts: { from?, to, subject, html }
// The Resend API key is stored as the RESEND_API_KEY Supabase secret — never in frontend code.
Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { to, subject, html, from } = await req.json()

    if (!to || !subject || !html) {
      return new Response(JSON.stringify({ error: 'to, subject, and html are required' }), { status: 400, headers: CORS })
    }

    const resendKey = Deno.env.get('RESEND_API_KEY')
    if (!resendKey) {
      return new Response(JSON.stringify({ error: 'RESEND_API_KEY not configured' }), { status: 500, headers: CORS })
    }

    const emailRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${resendKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: from || 'MedSync <insights@medsync.vet>',
        to: Array.isArray(to) ? to : [to],
        subject,
        html,
      }),
    })

    const data = await emailRes.json()
    if (!emailRes.ok) {
      return new Response(JSON.stringify({ error: 'Email send failed', detail: data }), { status: 502, headers: CORS })
    }

    return new Response(JSON.stringify({ ok: true, id: data.id }), { headers: CORS })

  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), { status: 500, headers: CORS })
  }
})
