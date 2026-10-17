// A picked photo the browser cannot decode must end in the sheet's failed state, not an unhandled rejection
// (PR #44 review). Runs with `make test-web`.
import { expect, test } from '@playwright/test'

import { tryPrepare } from './photo'

test('a photo whose preparation rejects gives null, so the sheet shows its failed state', async () => {
  const broken = async () => {
    throw new DOMException('The source image could not be decoded.', 'InvalidStateError')
  }
  expect(await tryPrepare(new Blob(['not an image']), broken)).toBeNull()
})

test('a photo that prepares is passed through unchanged', async () => {
  const jpeg = new Blob(['jpeg'], { type: 'image/jpeg' })
  const ok = async () => ({ jpeg, problem: null, measured: { brightness: 120, sharpness: 50 } })
  expect(await tryPrepare(new Blob(['photo']), ok)).toEqual(await ok())
})
