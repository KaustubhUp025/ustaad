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
  expect(mediaReducer(noMedia, request)).toEqual({ request, retakeReason: null, answers: 0 })
})

test('a poor photo keeps the sheet open on the same request and shows the reason', () => {
  const view = mediaReducer(mediaReducer(noMedia, request), result('Photo dhundhli hai'))
  expect(view).toEqual({ request, retakeReason: 'Photo dhundhli hai', answers: 1 })
})

test('a good photo after a retake closes the sheet', () => {
  const frames = [request, result('Photo dhundhli hai'), result(null)]
  expect(frames.reduce(mediaReducer, noMedia)).toEqual(noMedia)
})

test('a result for another request is ignored', () => {
  const open = mediaReducer(noMedia, request)
  expect(mediaReducer(open, result(null, 'r_2'))).toBe(open)
})

test('a new session closes the sheet; the server sends its open request again', () => {
  const open = mediaReducer(noMedia, request)
  const ready: ServerFrame = { v: 1, type: 'session_ready', session_id: 's_2', live_model: 'm', resumable: true }
  expect(mediaReducer(open, ready)).toEqual(noMedia)
  expect(mediaReducer(mediaReducer(open, ready), request)).toEqual({ request, retakeReason: null, answers: 0 })
})

test('a second retake with the same reason still counts as a new answer, so the sheet unlocks', () => {
  const once = mediaReducer(mediaReducer(noMedia, request), result('Photo dhundhli hai'))
  const twice = mediaReducer(once, result('Photo dhundhli hai'))
  expect(twice.answers).toBe(once.answers + 1)
  expect(twice.retakeReason).toBe('Photo dhundhli hai')
})
