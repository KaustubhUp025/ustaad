import { expect, test } from '@playwright/test'

import { addCaption } from './captionHistory'

test('retains the most recent bounded caption history', () => {
  let captions = [] as ReturnType<typeof addCaption>

  for (let number = 1; number <= 101; number += 1) {
    captions = addCaption(captions, { who: 'ustaad', text: `Caption ${number}`, final: true })
  }

  expect(captions).toHaveLength(100)
  expect(captions[0]?.text).toBe('Caption 2')
  expect(captions.at(-1)?.text).toBe('Caption 101')
})

test('replaces a partial caption with its finalized text', () => {
  const partial = addCaption([], { who: 'ustaad', text: 'Pehle outdoor', final: false })
  const finalized = addCaption(partial, { who: 'ustaad', text: 'Pehle outdoor unit ki PCB dekho.', final: true })

  expect(finalized).toEqual([
    { id: partial[0]?.id, who: 'ustaad', text: 'Pehle outdoor unit ki PCB dekho.', final: true },
  ])
  expect(addCaption(finalized, { who: 'ustaad', text: 'Agla turn', final: false })).toHaveLength(2)
})
