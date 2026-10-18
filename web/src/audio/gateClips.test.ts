import { expect, test } from '@playwright/test'

import bn from '@/i18n/bn.json' with { type: 'json' }
import en from '@/i18n/en.json' with { type: 'json' }
import hi from '@/i18n/hi.json' with { type: 'json' }
import ta from '@/i18n/ta.json' with { type: 'json' }
import te from '@/i18n/te.json' with { type: 'json' }

import clips from './gateClips.json' with { type: 'json' }

const GATES = ['G_MAINS_OFF', 'G_CAP_DISCHARGE'] as const

test('every gate has a recorded clip of its exact on-screen text in every language', () => {
  for (const [lang, strings] of Object.entries({ en, hi, te, ta, bn })) {
    for (const gate of GATES) {
      const shown = `${strings.repair.gate[gate]} ${strings.repair.evidence[gate]}`
      expect(clips[lang as keyof typeof clips]?.[gate], `${lang} ${gate}`).toBe(shown)
    }
  }
})
