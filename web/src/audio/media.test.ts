// The camera sheet's state (BUILD-GUIDE T17): opens on media_request, stays open with the reason on a retake,
// closes on a good result. Runs with `make test-web`.
import { expect, test } from '@playwright/test'

import type { ServerFrame } from './liveClient'
import { mediaReducer, noMedia } from './media'

const request: ServerFrame = {
  v: 1,
  type: 'media_request',
  request_id: 'r_1',
  kind: 'photo',
  target: 'Outdoor PCB, capacitor ke paas',
  framing_tip: 'Flash on, 20 cm door',
  max_seconds: null,
}
const result = (retake_reason: string | null, request_id = 'r_1'): ServerFrame => ({
  v: 1,
  type: 'media_result',
  request_id,
  matches_expected: retake_reason === null,
  confidence: retake_reason === null ? 0.9 : 0.41,
  retake_reason,
})

test('a media request opens the sheet with no retake reason', () => {
  expect(mediaReducer(noMedia, request)).toEqual({ request, retakeReason: null })
})

test('a poor photo keeps the sheet open on the same request and shows the reason', () => {
  const view = mediaReducer(mediaReducer(noMedia, request), result('Photo dhundhli hai'))
  expect(view).toEqual({ request, retakeReason: 'Photo dhundhli hai' })
})

test('a good photo after a retake closes the sheet', () => {
  const frames = [request, result('Photo dhundhli hai'), result(null)]
  expect(frames.reduce(mediaReducer, noMedia)).toEqual(noMedia)
})

test('a result for another request is ignored', () => {
  const open = mediaReducer(noMedia, request)
  expect(mediaReducer(open, result(null, 'r_2'))).toBe(open)
})
