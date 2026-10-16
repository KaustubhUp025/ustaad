import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { components } from './types'

export type InventoryItem = components['schemas']['InventoryItem']
type InventoryList = components['schemas']['InventoryListResponse']

const API_URL = import.meta.env.VITE_API_URL ?? ''
const KEY = ['inventory']

export function useInventory() {
  return useQuery({
    queryKey: KEY,
    queryFn: async (): Promise<InventoryList> => {
      const res = await fetch(`${API_URL}/api/inventory`)
      if (!res.ok) throw new Error(`inventory ${res.status}`)
      return res.json()
    },
  })
}

// One stepper tap: +1 or -1 on one part. The server applies it in a transaction and returns the whole list.
export function useStockStep() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({ part, delta }: { part: string; delta: 1 | -1 }): Promise<InventoryList> => {
      const res = await fetch(`${API_URL}/api/inventory`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deltas: [{ part, delta }] }),
      })
      if (!res.ok) throw new Error(`inventory ${res.status}`)
      return res.json()
    },
    onSuccess: (list) => client.setQueryData(KEY, list),
  })
}
