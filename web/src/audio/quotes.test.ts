import { expect, test } from '@playwright/test'

import type { ServerFrame } from './liveClient'
import { noQuotes, quotesReducer } from './quotes'
import fixture from '../routes/w/quotes.json' with { type: 'json' }

const frame = fixture.frame as Extract<ServerFrame, { type: 'quotes' }>

test('quotes frame retains the request id and its initial vendor item for REST polling', () => {
  expect(quotesReducer(noQuotes, frame)).toEqual({ quoteRequestId: 'qr_fixture', items: frame.items })
})

test('unrelated live frames retain the initial quotes while a vendor reply is pending', () => {
  const quotes = quotesReducer(noQuotes, frame)
  const caption: ServerFrame = { v: 1, type: 'caption', who: 'ustaad', text: 'Looking for parts', final: true }
  expect(quotesReducer(quotes, caption)).toBe(quotes)
})
