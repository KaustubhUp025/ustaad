import { expect, test } from '@playwright/test'

import type { Quote } from '@/api/quotes'

import { initialQuoteRows, rankedQuoteRows } from './quotesView'
import fixture from './quotes.json' with { type: 'json' }

const quote = fixture.response.quotes[0] as Quote

test('ranked REST quote is eligible only while its request is open', () => {
  expect(rankedQuoteRows([quote], null, true)[0]).toMatchObject({ id: 'q_voice', eligible: true, approved: false })
  expect(rankedQuoteRows([quote], null, false)[0].eligible).toBe(false)
})

test('initial websocket quote keeps an unknown distance absent instead of inventing one', () => {
  const row = initialQuoteRows([{ quote_id: 'q_waiting', vendor: 'Fixture Electricals', distance_km: null, price_inr: null, available: null, eta: null, from_voice: false }])[0]
  expect(row).toMatchObject({ distanceKm: null, priceInr: null, available: null, eligible: false })
})
