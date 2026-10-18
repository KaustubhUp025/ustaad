import { expect, test } from '@playwright/test'

import { pickVoice } from './speak'

const voice = (lang: string) => ({ lang }) as SpeechSynthesisVoice

test('the gate is read in a voice for his language', () => {
  expect(pickVoice([voice('en-US'), voice('hi-IN')], 'hi')?.lang).toBe('hi-IN')
  expect(pickVoice([voice('te_IN')], 'te')?.lang).toBe('te_IN')
})

test('English prefers the Indian English voice', () => {
  expect(pickVoice([voice('en-US'), voice('en-IN')], 'en')?.lang).toBe('en-IN')
})

test('with no voice for his language the gate is not read in another one', () => {
  expect(pickVoice([voice('en-US'), voice('en-IN')], 'ta')).toBeNull()
})
