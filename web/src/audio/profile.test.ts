// The live profile card (T21, G1): each profile_update frame adds what was just saved; a later answer replaces the
// earlier one for the same field. Runs with `make test-web`.
import { expect, test } from '@playwright/test'

import type { ServerFrame } from './liveClient'
import { hasProfile, noProfile, profileReducer } from './profile'

const update = (fields: Record<string, unknown>): ServerFrame => ({ v: 1, type: 'profile_update', fields })
const run = (...frames: ServerFrame[]) => frames.reduce(profileReducer, noProfile)

test('answers fill the card one by one and a new answer replaces the old one', () => {
  const view = run(update({ trades: ['ac', 'fridge'] }), update({ pincode: '201301' }), update({ trades: ['ac'] }))
  expect(view).toEqual({ trades: ['ac'], pincode: '201301' })
  expect(hasProfile(view)).toBe(true)
})

test('other frames leave the card alone, and an empty card is not shown', () => {
  const caption: ServerFrame = { v: 1, type: 'caption', who: 'ustaad', text: 'Test', final: true }
  expect(run(caption)).toBe(noProfile)
  expect(hasProfile(noProfile)).toBe(false)
})

test('fields the card does not know are ignored', () => {
  expect(run(update({ shop: 'Test Shop', unknown_field: 1 }))).toEqual({ shop: 'Test Shop' })
})
