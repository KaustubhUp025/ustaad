// The onboarding profile card (T21, G1): what save_profile_fields has saved so far, from profile_update frames.
import type { ServerFrame } from './liveClient'

export type StockAnswer = { part: string; qty: number | null }
export type ProfileView = {
  trades?: string[]
  brands?: string[]
  pincode?: string
  experience_yrs?: number
  stock?: StockAnswer[]
  shop?: string
  onboarding_done?: boolean
}

const FIELDS = ['trades', 'brands', 'pincode', 'experience_yrs', 'stock', 'shop', 'onboarding_done'] as const

export const noProfile: ProfileView = {}

export function profileReducer(view: ProfileView, frame: ServerFrame): ProfileView {
  if (frame.type !== 'profile_update') return view
  const known = Object.fromEntries(Object.entries(frame.fields).filter(([k]) => (FIELDS as readonly string[]).includes(k)))
  return { ...view, ...known }
}

export const hasProfile = (view: ProfileView) => Object.keys(view).length > 0
