import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const pat = Deno.env.get('GITHUB_PAT')
    if (!pat) {
      return new Response(JSON.stringify({ error: 'GITHUB_PAT secret not set' }), { status: 500, headers: CORS })
    }

    const res = await fetch(
      'https://api.github.com/repos/CODHenley/medsync/actions/workflows/intraday_sync.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github+json',
          'Authorization': `Bearer ${pat}`,
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main' }),
      }
    )

    if (res.status === 204) {
      return new Response(JSON.stringify({ ok: true, triggered: true }), { headers: CORS })
    }

    const body = await res.text()
    return new Response(JSON.stringify({ ok: false, error: `GitHub API ${res.status}: ${body}` }), {
      status: 502,
      headers: CORS,
    })
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), { status: 500, headers: CORS })
  }
})
