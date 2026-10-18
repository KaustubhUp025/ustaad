import { useQuery } from '@tanstack/react-query'

import { demoSession } from './session'
import type { components } from './types'

export type ImportStatus = components['schemas']['Import']['status']
export type FaultCard = components['schemas']['FaultCard']
export type Import = components['schemas']['Import']
export type ApplianceType = 'all' | NonNullable<FaultCard['appliance_type']>

const API_URL = import.meta.env?.VITE_API_URL ?? ''
const IMPORTS_KEY = ['dashboard', 'imports'] as const
const CARDS_KEY = ['dashboard', 'fault-cards'] as const

function headers(): HeadersInit {
  const token = demoSession()?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function read<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: headers() })
  if (!response.ok) throw new Error('dashboard request failed')
  return response.json()
}

export function readFaultCards(applianceType: ApplianceType = 'all') {
  const query = applianceType === 'all' ? '' : `?appliance_type=${encodeURIComponent(applianceType)}`
  return read<components['schemas']['FaultCardListResponse']>(`/api/fault-cards${query}`)
}

export function readImports() {
  return read<components['schemas']['ImportListResponse']>('/api/imports')
}

export function readImport(importId: string) {
  return read<Import>(`/api/imports/${encodeURIComponent(importId)}`)
}

export function useFaultCards(applianceType: ApplianceType) {
  return useQuery({
    queryKey: [...CARDS_KEY, applianceType],
    queryFn: () => readFaultCards(applianceType),
    retry: false,
  })
}

export function useImports() {
  return useQuery({
    queryKey: IMPORTS_KEY,
    queryFn: readImports,
    refetchInterval: 2_000,
    refetchIntervalInBackground: false,
    retry: false,
  })
}

export function useImport(importId: string | null) {
  return useQuery({
    queryKey: [...IMPORTS_KEY, importId],
    queryFn: () => readImport(importId!),
    enabled: importId !== null,
    refetchInterval: 2_000,
    refetchIntervalInBackground: false,
    retry: false,
  })
}

const SAFE_IMPORT_ERRORS = new Map([
  ['The chat import could not be processed.', 'pipeline_failed'],
  ['The chat date order could not be determined, so the import was not processed.', 'date_order_ambiguous'],
  ['One chat attachment could not be read, so it was kept without enrichment.', 'attachment_failed'],
  ['One chat thread could not be read, so it was skipped.', 'thread_failed'],
])

export function safeImportError(error: string) {
  return SAFE_IMPORT_ERRORS.get(error) ?? 'pipeline_failed'
}

// Test-only explicit demo data. Dashboard routes never import this fixture as live data.
export const dashboardFixture = {
  importHistory: (['queued', 'parsing', 'transcribing', 'extracting', 'done', 'failed'] as const).map((status) => ({
    id: `i_demo_${status}`,
    status,
    filesTotal: 18,
    audioTotal: 14,
    audioDone: 0,
    threads: 0,
    cardsCreated: 0,
    cardsNeedingReview: 0,
    errors: status === 'failed' ? ['The chat import could not be processed.'] : [],
  })),
}
