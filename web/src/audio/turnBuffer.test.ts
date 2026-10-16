import { expect, test } from '@playwright/test'

import { MAX_BUFFERED_BYTES, TurnBuffer } from './turnBuffer'

const start = JSON.stringify({ v: 1, type: 'ptt', state: 'start' })
const end = JSON.stringify({ v: 1, type: 'ptt', state: 'end' })

test('a turn spoken while reconnecting is sent in order once the socket is back', () => {
  const buffer = new TurnBuffer()
  const chunk = new ArrayBuffer(3200)
  buffer.push(start)
  buffer.push(chunk)
  buffer.push(end)
  const sent: (string | ArrayBuffer)[] = []
  buffer.flush((data) => sent.push(data))
  expect(sent).toEqual([start, chunk, end])
  buffer.flush((data) => sent.push(data))
  expect(sent).toHaveLength(3)
})

test('audio past about 5 s is dropped, but the end of the turn still goes', () => {
  const buffer = new TurnBuffer()
  buffer.push(start)
  for (let i = 0; i < 60; i++) buffer.push(new ArrayBuffer(3200))
  buffer.push(end)
  const sent: (string | ArrayBuffer)[] = []
  buffer.flush((data) => sent.push(data))
  const audioBytes = sent.filter((d) => d instanceof ArrayBuffer).reduce((n, d) => n + (d as ArrayBuffer).byteLength, 0)
  expect(audioBytes).toBeLessThanOrEqual(MAX_BUFFERED_BYTES)
  expect(sent.at(0)).toBe(start)
  expect(sent.at(-1)).toBe(end)
})

test('a failed reconnect drops what was held', () => {
  const buffer = new TurnBuffer()
  buffer.push(start)
  buffer.push(new ArrayBuffer(3200))
  buffer.clear()
  const sent: (string | ArrayBuffer)[] = []
  buffer.flush((data) => sent.push(data))
  expect(sent).toEqual([])
})
