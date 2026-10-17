import type { QuoteItem, ServerFrame } from './liveClient'

export type QuotesView = { quoteRequestId: string | null; items: QuoteItem[] }

export const noQuotes: QuotesView = { quoteRequestId: null, items: [] }

// The agent sends this frame once when it opens a vendor request. REST then provides its ranked updates.
export function quotesReducer(view: QuotesView, frame: ServerFrame): QuotesView {
  if (frame.type !== 'quotes') return view
  return { quoteRequestId: frame.quote_request_id, items: frame.items }
}
