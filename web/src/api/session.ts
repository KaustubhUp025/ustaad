// "Try the demo" (POST /api/demo/session, rest.md): no login; the server hands out a signed 24 h token for a seeded
// demo worker. The token is kept for this tab; storage can throw in private windows, so it is also kept in memory.
import type { components } from './types'

type DemoSession = components['schemas']['DemoSessionResponse']
type DemoRequest = Partial<components['schemas']['DemoSessionRequest']>
export type Worker = components['schemas']['Worker']

const API_URL = import.meta.env?.VITE_API_URL ?? ''
const KEY = 'ustaad.session'
let current: DemoSession | null = null

// With `{ onboarding: true, lang }` the server makes a new, empty demo worker for the onboarding interview (T21).
export async function startDemo(request?: DemoRequest): Promise<DemoSession> {
  const res = await fetch(`${API_URL}/api/demo/session`, {
    method: 'POST',
    ...(request && { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) }),
  })
  if (!res.ok) throw new Error(`demo session ${res.status}`)
  current = await res.json()
  try {
    sessionStorage.setItem(KEY, JSON.stringify(current))
  } catch {
    // kept in memory only: a refresh asks him to start the demo again
  }
  return current!
}

export function demoSession(): DemoSession | null {
  if (current) return current
  try {
    const stored = sessionStorage.getItem(KEY)
    current = stored ? JSON.parse(stored) : null
  } catch {
    current = null
  }
  return current
}
