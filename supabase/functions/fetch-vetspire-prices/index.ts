import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

// Query VetSpire for up to BATCH_SIZE products at once using GraphQL aliases
const BATCH_SIZE = 25

async function fetchVetspireBatch(
  token: string,
  items: Array<{ vetspire_product_id: string; product_id: string; name: string; unit_price: number | null }>
): Promise<Array<{ product_id: string; vetspire_product_id: string; name: string; unit_price: number | null; vetspire_cost: number | null; error?: string }>> {
  // Build a batched query using aliases: p_<idx>: product(id: "...") { ... }
  const aliases = items.map((item, idx) =>
    `p_${idx}: product(id: "${item.vetspire_product_id}") { id unitCost realUnitCost }`
  ).join('\n      ')

  const query = `query FetchProductCosts {\n      ${aliases}\n    }`

  const vsRes = await fetch('https://api.vetspire.com/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token,
      'Origin': 'https://scoutcare.vetspire.com',
    },
    body: JSON.stringify({ query }),
  })

  const rawText = await vsRes.text()
  let vsJson: any
  try { vsJson = JSON.parse(rawText) } catch {
    return items.map(item => ({ ...item, vetspire_cost: null, error: `Non-JSON response (HTTP ${vsRes.status})` }))
  }

  if (!vsJson.data) {
    const errMsg = vsJson.errors ? JSON.stringify(vsJson.errors) : 'No data field'
    return items.map(item => ({ ...item, vetspire_cost: null, error: errMsg }))
  }

  return items.map((item, idx) => {
    const node = vsJson.data[`p_${idx}`]
    if (!node) return { ...item, vetspire_cost: null, error: 'Product not found in VetSpire' }
    const vetspire_cost = node.realUnitCost ?? node.unitCost ?? null
    return {
      product_id: item.product_id,
      vetspire_product_id: item.vetspire_product_id,
      name: item.name,
      unit_price: item.unit_price,
      vetspire_cost: vetspire_cost != null ? parseFloat(vetspire_cost) : null,
    }
  })
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const token = Deno.env.get('Medsync_API_Key')
    if (!token) {
      return new Response(JSON.stringify({ error: 'Medsync_API_Key secret not set' }), { status: 500, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // If caller passes explicit product list, use it; otherwise load all from DB
    const body = req.method === 'POST' ? await req.json().catch(() => ({})) : {}
    let products: Array<{ vetspire_product_id: string; product_id: string; name: string; unit_price: number | null }>

    if (Array.isArray(body.products) && body.products.length > 0) {
      products = body.products
    } else {
      // Load all products that have a vetspire_product_id
      const { data, error } = await supabase
        .from('products')
        .select('id, name, unit_price, vetspire_product_id')
        .not('vetspire_product_id', 'is', null)
        .limit(2000)

      if (error) throw new Error('Supabase error: ' + error.message)
      products = (data || []).map((p: any) => ({
        product_id: String(p.id),
        vetspire_product_id: String(p.vetspire_product_id),
        name: p.name || '',
        unit_price: p.unit_price != null ? parseFloat(p.unit_price) : null,
      }))
    }

    if (products.length === 0) {
      return new Response(JSON.stringify({ results: [], total: 0 }), { headers: CORS })
    }

    // Process in batches
    const results: any[] = []
    for (let i = 0; i < products.length; i += BATCH_SIZE) {
      const batch = products.slice(i, i + BATCH_SIZE)
      const batchResults = await fetchVetspireBatch(token, batch)
      results.push(...batchResults)
    }

    return new Response(JSON.stringify({ results, total: results.length }), { headers: CORS })

  } catch (err) {
    console.error('fetch-vetspire-prices error:', err)
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: CORS,
    })
  }
})
