import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { product_id, vetspire_product_id, unit_cost, sku } = await req.json()

    if (!product_id) {
      return new Response(JSON.stringify({ error: 'product_id is required' }), { status: 400, headers: CORS })
    }
    if (unit_cost == null && sku == null) {
      return new Response(JSON.stringify({ error: 'unit_cost or sku is required' }), { status: 400, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // Build the update payload — only include fields that were provided
    const update: Record<string, unknown> = {}

    if (unit_cost != null) {
      const cost = parseFloat(unit_cost)
      if (isNaN(cost) || cost < 0) {
        return new Response(JSON.stringify({ error: 'unit_cost must be a non-negative number' }), { status: 400, headers: CORS })
      }
      update.unit_cost = cost
    }

    if (sku != null) {
      update.sku = String(sku).trim() || null
    }

    // 1. Update products table in Supabase
    const { error: dbErr } = await supabase
      .from('products')
      .update(update)
      .eq('id', product_id)

    if (dbErr) throw new Error('Supabase update failed: ' + dbErr.message)

    // 2. Push cost and/or SKU to VetSpire if we have a vetspire_product_id
    let vetspireSynced = false
    let vetspireError: string | null = null

    const hasVetspireUpdate = vetspire_product_id && (unit_cost != null || sku != null)
    if (hasVetspireUpdate) {
      const token = Deno.env.get('Medsync_API_Key')
      if (!token) {
        vetspireError = 'Medsync_API_Key secret not set'
      } else {
        try {
          // Build VetSpire input — include whichever fields were provided
          const vsInput: Record<string, unknown> = {}
          if (unit_cost != null) {
            const cost = update.unit_cost as number
            vsInput.unitCost = cost
            vsInput.realUnitCost = cost
          }
          if (sku != null) {
            vsInput.sku = String(sku).trim() || null
          }

          const vsRes = await fetch('https://api.vetspire.com/graphql', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token,
              'Origin': 'https://scoutcare.vetspire.com',
            },
            body: JSON.stringify({
              query: `mutation UpdateProduct($id: ID!, $input: ProductInput!) {
                updateProduct(id: $id, input: $input) { id unitCost realUnitCost sku }
              }`,
              variables: {
                id: String(vetspire_product_id),
                input: vsInput,
              },
            }),
          })

          const vsJson = await vsRes.json().catch(() => null)
          if (vsJson?.errors?.length) {
            vetspireError = 'VetSpire error: ' + JSON.stringify(vsJson.errors)
          } else if (vsJson?.data?.updateProduct) {
            vetspireSynced = true
          } else {
            vetspireError = `Unexpected VetSpire response (HTTP ${vsRes.status})`
          }
        } catch (e) {
          vetspireError = 'VetSpire fetch failed: ' + String(e)
        }
      }
    }

    return new Response(JSON.stringify({
      ok: true,
      product_id,
      vetspire_product_id: vetspire_product_id || null,
      unit_cost: update.unit_cost ?? null,
      sku: update.sku ?? null,
      vetspire_synced: vetspireSynced,
      vetspire_error: vetspireError,
    }), { headers: CORS })

  } catch (err) {
    console.error('push-unit-cost error:', err)
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: CORS,
    })
  }
})
