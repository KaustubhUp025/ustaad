import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { demoSession } from './session'
import type { components } from './types'

export type Quote = components['schemas']['Quote']
export type QuotesResponse = components['schemas']['QuotesResponse']

const API_URL = import.meta.env.VITE_API_URL ?? ''
const key = (requestId: string) => ['quotes', requestId] as const

function headers(): HeadersInit {
  const token = demoSession()?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function readQuotes(requestId: string): Promise<QuotesResponse> {
  const response = await fetch(`${API_URL}/api/quotes/${encodeURIComponent(requestId)}`, { headers: headers() })
  if (!response.ok) throw new Error('quotes request failed')
  return response.json()
}

async function approveQuote(quoteId: string): Promise<QuotesResponse> {
  const response = await fetch(`${API_URL}/api/quotes/${encodeURIComponent(quoteId)}/approve`, {
    method: 'POST',
    headers: headers(),
  })
  if (!response.ok) throw new Error('quote approval failed')
  return response.json()
}

// Vendor replies arrive through the Telegram webhook, not the phone socket, so refresh while this card is visible.
export function useQuotes(requestId: string | null) {
  return useQuery({
    queryKey: key(requestId ?? ''),
    queryFn: () => readQuotes(requestId!),
    enabled: requestId !== null,
    refetchInterval: 2_000,
    refetchIntervalInBackground: false,
    retry: false,
  })
}

export function useApproveQuote(requestId: string | null) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: approveQuote,
    onSuccess: (response) => {
      if (requestId) client.setQueryData(key(requestId), response)
    },
  })
}
