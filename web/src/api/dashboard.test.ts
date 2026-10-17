import { expect, test } from '@playwright/test'

import { dashboardFixture, filterCards, safeImportError } from './dashboard'

test('knowledge cards filter by appliance type and review status', () => {
  expect(filterCards(dashboardFixture.cards, 'washing_machine').map((card) => card.id)).toEqual(['fc_washer_1'])
  expect(dashboardFixture.cards.filter((card) => card.reviewStatus === 'needs_review')).toHaveLength(2)
})

test('import errors expose only fixed safe messages', () => {
  expect(safeImportError('pipeline_failed')).toBe('pipeline_failed')
  expect(safeImportError('gs://bucket/private.zip token=secret')).toBe('pipeline_failed')
})

test('fixture covers every contracted import lifecycle state', () => {
  expect(dashboardFixture.importHistory.map((item) => item.status)).toEqual([
    'queued',
    'parsing',
    'transcribing',
    'extracting',
    'done',
    'failed',
  ])
})
