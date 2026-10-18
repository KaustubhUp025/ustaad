// Which "Try the demo" samples the camera sheet offers. Runs with `make test-web` (Playwright test runner, no browser).
import { expect, test } from '@playwright/test'

import { samplesFor } from './samples'

test('a safety gate offers only samples that show that gate', () => {
  // Phone test (Oct 17): the E6 display and the energy label were offered for the MCB OFF photo.
  expect(samplesFor('G_MAINS_OFF').map((s) => [s.name, s.provenance])).toEqual([['samples.mcbOff', 'ownPhoto']])
  // The only capacitor sample reads 5.03 V, above the 5 V limit: it shows the gate refusing, labelled AI-generated.
  expect(samplesFor('G_CAP_DISCHARGE').map((s) => [s.name, s.provenance])).toEqual([['samples.meterHigh', 'aiGenerated']])
})

test('a photo request without a gate offers the appliance samples and the PCB retake pair', () => {
  expect(samplesFor(undefined).map((s) => [s.name, s.provenance])).toEqual([
    ['samples.displayE6', 'publicPost'],
    ['samples.voltasLabel', 'publicPost'],
    ['samples.pcbClear', 'publicPost'],
    ['samples.pcbBlurry', 'publicPost'],
  ])
})
