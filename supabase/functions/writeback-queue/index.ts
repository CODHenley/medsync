import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'content-type', 'Content-Type': 'application/json' }
const SUPA_URL = Deno.env.get('SUPABASE_URL')
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
async function getVetspireToken() {
  const token = Deno.env.get('VETSPIRE_API_TOKEN')
  if (!token) throw new Error('VETSPIRE_API_TOKEN secret not set')
  return token
}

async function getCurrentStock(token, productId, locationId) {
  const r = await fetch('https://api.vetspire.com/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'Origin': 'https://scoutcare.vetspire.com' },
    body: JSON.stringify({
      query: 'query getStock($locationId: ID!, $limit: Int, $offset: Int) { products(onlyTrackInventory: true, onlyEnabledAt: $locationId, limit: $limit, offset: $offset) { id inventoryLevels(locationId: $locationId) { stock } } }',
      variables: { locationId: locationId, limit: 500, offset: 0 }
    })
  })
  const d = await r.json()
  const prods = d.data?.products || []
  const match = prods.find(p => String(p.id) === String(productId))
  if (!match) return 0
  return (match.inventoryLevels || []).reduce((sum, l) => sum + parseFloat(l.stock || 0), 0)
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS })
  try {
    const body = await req.json()
    const supabase = createClient(SUPA_URL, SERVICE_KEY)
    const actualCount = parseFloat(body.actual_count)

    // 1. Get live Vetspire stock first so we can calculate real delta
    const token = await getVetspireToken()
    const currentStock = await getCurrentStock(token, body.vetspire_product_id, body.vetspire_location_id)
    const quantityChange = actualCount - currentStock

    // 2. Log to queue
    const { data: row, error: insertErr } = await supabase
      .from('vetspire_writeback_queue')
      .insert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, quantity_change: quantityChange, lot_number: body.lot_number || null, expiration_date: body.expiration_date || null, status: 'processing' })
      .select().single()
    if (insertErr) throw new Error('Insert failed: ' + JSON.stringify(insertErr))

    // 3. Update Supabase snapshot
    await supabase.from('inventory_snapshots')
      .upsert({ vetspire_product_id: body.vetspire_product_id, vetspire_location_id: body.vetspire_location_id, on_hand: actualCount, snapshot_date: new Date().toISOString().slice(0,10), product_name: body.product_name || '', location_name: body.location_name || '' }, { onConflict: 'vetspire_product_id,vetspire_location_id,snapshot_date' })

    // 4. Send adjustment to Vetspire only if there is a real nonzero delta
    let adjId = null
    if (quantityChange !== 0 && !isNaN(quantityChange)) {
      const result = await fetch('https://api.vetspire.com/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'Origin': 'https://scoutcare.vetspire.com' },
        body: JSON.stringify({
          query: 'mutation CreateInventoryAdjustment($input: InventoryAdjustmentInput!) { createInventoryAdjustment(input: $input) { id quantityChange } }',
          variables: { input: { locationId: body.vetspire_location_id, productId: body.vetspire_product_id, quantityChange: quantityChange, lotNumber: body.lot_number || null, expirationDate: body.expiration_date || null, isWastage: false } }
        })
      })
      const resultJson = await result.json()
      if (resultJson.errors) throw new Error('Vetspire GQL error: ' + JSON.stringify(resultJson.errors))
      adjId = resultJson.data?.createInventoryAdjustment?.id
    }

    // 5. Mark processed
    await supabase.from('vetspire_writeback_queue').update({ status: 'processed', processed_at: new Date().toISOString() }).eq('id', row.id)

    return new Response(JSON.stringify({ ok: true, adjustment_id: adjId, debug: { actual_count: actualCount, currentStock, quantityChange } }), { headers: CORS })
  } catch (e) {
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : String(e) }), { status: 400, headers: CORS })
  }
})
