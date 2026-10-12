import { useQuery } from '@tanstack/react-query'

// Deployed builds leave VITE_API_URL empty and use same-origin /api (Hosting rewrite).
const API_URL = import.meta.env.VITE_API_URL ?? ''

export function useHealth() {
  return useQuery({
    queryKey: ['healthz'],
    queryFn: async (): Promise<{ ok: boolean }> => {
      const res = await fetch(`${API_URL}/api/healthz`)
      if (!res.ok) throw new Error(`healthz ${res.status}`)
      return res.json()
    },
    retry: false,
  })
}
