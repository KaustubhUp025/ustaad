import { expect, test } from '@playwright/test'

import bn from './bn.json' with { type: 'json' }
import en from './en.json' with { type: 'json' }
import hi from './hi.json' with { type: 'json' }
import ta from './ta.json' with { type: 'json' }
import te from './te.json' with { type: 'json' }

// Ustaad answers in the language of the latest words, so a tapped question must be in the job's language: Hinglish
// questions on the English job made it answer in Hindi (phone test, Oct 18).
type Strings = { live: { ex1: string; ex2: string; ex3: string } }
const examples = (strings: Strings) => [strings.live.ex1, strings.live.ex2, strings.live.ex3]

test('the English job offers English questions, not the Hindi ones', () => {
  const hindi = examples(hi)
  for (const q of examples(en)) expect(hindi).not.toContain(q)
})

test('Telugu, Tamil and Bengali questions are written in their own script', () => {
  const scripts: [Strings, RegExp][] = [
    [te, /[\u0C00-\u0C7F]/],
    [ta, /[\u0B80-\u0BFF]/],
    [bn, /[\u0980-\u09FF]/],
  ]
  for (const [strings, script] of scripts) for (const q of examples(strings)) expect(q).toMatch(script)
})
