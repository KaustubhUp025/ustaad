import { expect, test } from '@playwright/test'

import { isNearCaptionBottom } from './captionScroll'

test('only follows captions when the reader is near the bottom', () => {
  expect(isNearCaptionBottom({ scrollHeight: 1000, scrollTop: 760, clientHeight: 200 })).toBe(true)
  expect(isNearCaptionBottom({ scrollHeight: 1000, scrollTop: 620, clientHeight: 200 })).toBe(false)
})
