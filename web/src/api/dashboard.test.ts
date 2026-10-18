import { expect, test } from '@playwright/test'

import { dashboardFixture, readFaultCards, readImport, readImports, safeImportError } from './dashboard'

test('dashboard reads fault cards from the documented endpoint and appliance filter', async () => {
  const calls: string[] = []
  const original = globalThis.fetch
  globalThis.fetch = async (input) => {
    calls.push(String(input))
    return Response.json({ items: [{ id: 'fc_live' }], next: null })
  }

  try {
    await expect(readFaultCards('split_ac')).resolves.toEqual({ items: [{ id: 'fc_live' }], next: null })
  } finally {
    globalThis.fetch = original
  }

  expect(calls).toEqual(['/api/fault-cards?appliance_type=split_ac'])
})

test('dashboard reads the signed-in worker import list and selected import detail', async () => {
  const calls: string[] = []
  const original = globalThis.fetch
  globalThis.fetch = async (input) => {
    calls.push(String(input))
    return Response.json({ items: [] })
  }

  try {
    await readImports()
    await readImport('i_live')
  } finally {
    globalThis.fetch = original
  }

  expect(calls).toEqual(['/api/imports', '/api/imports/i_live'])
})

test('import errors expose only fixed safe messages', () => {
  expect(safeImportError('The chat import could not be processed.')).toBe('pipeline_failed')
  expect(safeImportError('One chat attachment could not be read, so it was kept without enrichment.')).toBe(
    'attachment_failed',
  )
  expect(safeImportError('gs://bucket/private.zip token=secret')).toBe('pipeline_failed')
})

test('the retained fixture is explicit demo/test data only and covers every lifecycle state', () => {
  expect(dashboardFixture.importHistory.map((item) => item.status)).toEqual([
    'queued',
    'parsing',
    'transcribing',
    'extracting',
    'done',
    'failed',
  ])
})

test('a dashboard opened without a session starts the demo one and reads again with its token', async () => {
  const calls: string[] = []
  const original = globalThis.fetch
  globalThis.fetch = async (input, init) => {
    const auth = new Headers(init?.headers).get('Authorization')
    calls.push(`${init?.method ?? 'GET'} ${String(input)} ${auth ?? '-'}`)
    if (String(input) === '/api/demo/session') return Response.json({ token: 't_demo' })
    return auth ? Response.json({ items: [] }) : new Response(null, { status: 401 })
  }

  try {
    await expect(readImports()).resolves.toEqual({ items: [] })
  } finally {
    globalThis.fetch = original
  }

  expect(calls).toEqual(['GET /api/imports -', 'POST /api/demo/session -', 'GET /api/imports Bearer t_demo'])
})
