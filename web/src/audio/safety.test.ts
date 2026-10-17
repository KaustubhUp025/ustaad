// SAFETY.md test 10 and the rest of the repair screen state. Runs with `make test-web` (Playwright test runner,
// no browser needed).
import { expect, test } from '@playwright/test'

import type { ServerFrame } from './liveClient'
import { type RepairView, noRepair, repairReducer, stepLines } from './safety'

type Of = Extract<ServerFrame, { type: 'step_card' }>

const source = { kind: 'general', label: 'General guidance', audio_uri: null, doc: null, page: null } as const
const gate: ServerFrame = {
  v: 1,
  type: 'safety_gate',
  gate_id: 'G_MAINS_OFF',
  message: 'Safety check first',
  required_evidence: 'MCB OFF photo',
}
const step = (hazard: 'none' | 'HV' | 'capacitor', n = 1): ServerFrame => ({
  v: 1,
  type: 'step_card',
  job_id: 'j_1',
  n,
  of: 3,
  instruction: `Test step ${n}`,
  hazard,
  source,
})
const result = (passed: boolean): ServerFrame => ({
  v: 1,
  type: 'gate_result',
  gate_id: 'G_MAINS_OFF',
  passed,
  reason: passed ? null : 'No MCB in the photo',
})
const run = (...frames: ServerFrame[]): RepairView => frames.reduce(repairReducer, noRepair)

test('10: a hazardous step_card injected while a gate is open is dropped and the gate stays', () => {
  for (const hazard of ['HV', 'capacitor'] as const) {
    const view = run(gate, step(hazard))
    expect(view.gate?.gate_id).toBe('G_MAINS_OFF')
    expect(view.step).toBeNull()
  }
})

test('a hazardous step injected while a gate is open stays dropped after the gate passes', () => {
  const view = run(gate, step('HV'), result(true))
  expect(view.gate).toBeNull()
  expect(view.step).toBeNull()
})

test('a failed gate check keeps the gate and shows the reason', () => {
  const view = run(gate, result(false))
  expect(view.gate?.gate_id).toBe('G_MAINS_OFF')
  expect(view.failReason).toBe('No MCB in the photo')
})

test('a passed gate clears the gate, then the next step shows', () => {
  const view = run(gate, result(true), step('HV', 2))
  expect(view.gate).toBeNull()
  expect(view.step?.n).toBe(2)
})

test('a step with no hazard shows when no gate is open', () => {
  expect(run(step('none')).step?.n).toBe(1)
})

test('a safety_stop shows the stop until a later step arrives', () => {
  const stop: ServerFrame = { v: 1, type: 'safety_stop', reason: 'refrigerant', message: 'Stopped for safety' }
  expect(run(step('none'), stop).stop?.reason).toBe('refrigerant')
  expect(run(stop, step('none', 2)).stop).toBeNull()
})

test('the step card shows the translation with the original small, and only the original when there is none', () => {
  const card = (instruction_translated: string | null) => ({ ...(step('none') as Of), instruction_translated })
  expect(stepLines(card('Test translated'))).toEqual({ main: 'Test translated', original: 'Test step 1' })
  expect(stepLines(card(null))).toEqual({ main: 'Test step 1', original: null })
  expect(stepLines(step('none') as Of)).toEqual({ main: 'Test step 1', original: null })
  expect(stepLines(card('Test step 1'))).toEqual({ main: 'Test step 1', original: null })
})
