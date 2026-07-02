import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'content-type, authorization, apikey',
  'Content-Type': 'application/json',
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })

  try {
    const { flag_id, vetspire_product_id, new_unit_cost, resolved_by } = await req.json()

    if (!flag_id || new_unit_cost == null) {
      return new Response(JSON.stringify({ error: 'flag_id and new_unit_cost are required' }), { status: 400, headers: CORS })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    let updatedCost = parseFloat(new_unit_cost)
    let vetspireSynced = false

    let vetspireError: string | null = null

    // Call VetSpire only when we have a product ID
    if (vetspire_product_id) {
      const token = Deno.env.get('Medsync_API_Key')
      if (!token) {
        vetspireError = 'Medsync_API_Key secret not set'
        console.error('update-unit-cost: VetSpire skipped —', vetspireError)
      } else {
        try {
          const vsRes = await fetch('https://api.vetspire.com/graphql', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token,
              'Origin': 'https://scoutcare.vetspire.com',
            },
            body: JSON.stringify({
              query: `mutation UpdateProductCost($id: ID!, $input: ProductInput!) {
                updateProduct(id: $id, input: $input) {
                  id
                  unitCost
                  realUnitCost
                }
              }`,
              variables: {
                id: String(vetspire_product_id),
                input: { unitCost: updatedCost, realUnitCost: updatedCost },
              },
            }),
          })

          const rawText = await vsRes.text()
          let vsJson: any
          try {
            vsJson = JSON.parse(rawText)
          } catch {
            vetspireError = `VetSpire returned non-JSON (HTTP ${vsRes.status}): ${rawText.slice(0, 200)}`
            console.error('update-unit-cost: VetSpire parse error —', vetspireError)
          }

          if (vsJson) {
            if (vsJson.errors && vsJson.errors.length > 0) {
              vetspireError = 'VetSpire error: ' + JSON.stringify(vsJson.errors)
              console.error('update-unit-cost: VetSpire GQL error —', vetspireError)
            } else {
              updatedCost = vsJson.data?.updateProduct?.realUnitCost ?? vsJson.data?.updateProduct?.unitCost ?? updatedCost
              vetspireSynced = true
            }
          }
        } catch (vsErr) {
          vetspireError = 'VetSpire fetch failed: ' + String(vsErr)
          console.error('update-unit-cost: VetSpire fetch error —', vetspireError)
        }
      }
    }

    console.log('update-unit-cost: patching flag', flag_id, 'synced=', vetspireSynced, 'cost=', updatedCost)

    // Mark flag resolved in Supabase
    const { error: patchErr } = await supabase
      .from('price_review_flags')
      .update({
        status: vetspireSynced ? 'approved_synced' : 'approved_pending_sync',
        vetspire_synced: vetspireSynced,
        resolved_by: resolved_by || null,
        resolved_at: new Date().toISOString(),
      })
      .eq('id', flag_id)

    if (patchErr) {
      console.error('patch error:', JSON.stringify(patchErr))
      throw new Error('Supabase patch failed: ' + patchErr.message + ' | code: ' + patchErr.code + ' | details: ' + patchErr.details)
    }

    console.log('update-unit-cost: patch ok, fetching product_id from flag')

    // Also update unit_price in local products table if product_id is available
    const { data: flagRow, error: fetchErr } = await supabase
      .from('price_review_flags')
      .select('product_id')
      .eq('id', flag_id)
      .single()

    if (fetchErr && fetchErr.code !== 'PGRST116') {
      console.error('fetch flag error:', JSON.stringify(fetchErr))
    }

    if (flagRow?.product_id) {
      console.log('update-unit-cost: updating product', flagRow.product_id)
      const { error: prodErr } = await supabase
        .from('products')
        .update({ unit_price: updatedCost })
        .eq('id', flagRow.product_id)
      if (prodErr) console.error('product update error:', JSON.stringify(prodErr))
    }

    return new Response(JSON.stringify({
      ok: true,
      vetspire_product_id: vetspire_product_id || null,
      vetspire_synced: vetspireSynced,
      vetspire_error: vetspireError,
      new_unit_cost: updatedCost,
      flag_id,
    }), { headers: CORS })

  } catch (err) {
    console.error('update-unit-cost error:', err)
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
      status: 500,
      headers: CORS,
    })
  }
})
