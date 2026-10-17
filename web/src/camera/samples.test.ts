// Which "Try the demo" samples the camera sheet offers. Runs with `make test-web` (Playwright test runner, no browser).
import { expect, test } from '@playwright/test'

import { samplesFor } from './samples'

test('a safety gate offers only samples that show that gate', () => {
  // Phone test (Oct 17): the E6 display and the energy label were offered for the MCB OFF photo.
  expect(samplesFor('G_MAINS_OFF').every((s) => s.gate === 'G_MAINS_OFF')).toBe(true)
  expect(samplesFor('G_CAP_DISCHARGE')).toEqual([])
})

test('a photo request without a gate offers the appliance samples', () => {
  expect(samplesFor(undefined).map((s) => s.name)).toEqual(['samples.displayE6', 'samples.voltasLabel'])
})
