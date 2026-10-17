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
