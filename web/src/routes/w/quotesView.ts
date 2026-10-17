import type { Quote } from '@/api/quotes'
import type { QuoteItem } from '@/audio/liveClient'

export type QuoteRow = {
  id: string
  vendor: string
  available: boolean | null
  priceInr: number | null
  eta: string | null
  distanceKm: number | null
  fromVoice: boolean
  eligible: boolean
  approved: boolean
}

export function initialQuoteRows(items: QuoteItem[]): QuoteRow[] {
  return items.map((item) => ({
    id: item.quote_id,
    vendor: item.vendor,
    available: item.available,
    priceInr: item.price_inr,
    eta: item.eta,
    distanceKm: item.distance_km,
    fromVoice: item.from_voice,
    eligible: false,
    approved: false,
  }))
}

export function rankedQuoteRows(quotes: Quote[], approvedQuoteId: string | null, requestOpen: boolean): QuoteRow[] {
  return quotes.map((quote) => ({
    id: quote.id,
    vendor: quote.vendor_name,
    available: quote.available,
    priceInr: quote.price_inr,
    eta: quote.eta,
    distanceKm: null,
    fromVoice: quote.from_voice,
    eligible: requestOpen && quote.state === 'QUOTED' && quote.available === true,
    approved: approvedQuoteId === quote.id || quote.state === 'CONFIRMED',
  }))
}
