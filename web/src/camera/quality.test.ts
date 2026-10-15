// The phone-side photo check (BUILD-GUIDE T17): catches a very dark or very blurry photo before any upload.
// Runs with `make test-web`.
import { expect, test } from '@playwright/test'

import { photoProblem, measure } from './quality'

// A grey test card: w x h pixels, RGBA, from a luma function of (x, y).
function card(luma: (x: number, y: number) => number, w = 64, h = 48) {
  const data = new Uint8ClampedArray(w * h * 4)
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = 4 * (y * w + x)
      data[i] = data[i + 1] = data[i + 2] = luma(x, y)
      data[i + 3] = 255
    }
  return { data, width: w, height: h }
}

const checker = (on: number, off: number) => card((x, y) => (((x >> 2) + (y >> 2)) % 2 ? on : off))

test('a sharp, well lit photo has no problem', () => {
  expect(photoProblem(measure(checker(220, 40)))).toBeNull()
})

test('a very dark photo is caught', () => {
  expect(photoProblem(measure(checker(30, 5)))).toBe('dark')
})

test('a flat, featureless photo (heavy blur) is caught', () => {
  expect(photoProblem(measure(card(() => 128)))).toBe('blurry')
})

test('brightness and sharpness are reported for tuning', () => {
  const m = measure(checker(220, 40))
  expect(m.brightness).toBeGreaterThan(100)
  expect(m.sharpness).toBeGreaterThan(1000)
})
