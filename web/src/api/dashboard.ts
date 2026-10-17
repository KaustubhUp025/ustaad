export type ImportStatus = 'queued' | 'parsing' | 'transcribing' | 'extracting' | 'done' | 'failed'
export type ApplianceType = 'all' | 'split_ac' | 'washing_machine' | 'unknown'
export type ReviewStatus = 'approved' | 'needs_review'
export type ImageOrigin = 'ai_generated' | 'public_post'

export type KnowledgeCard = {
  id: string
  applianceType: Exclude<ApplianceType, 'all'>
  applianceLabel: string
  brand: string
  code: string
  symptom: string
  source: string
  confidence: number | null
  reviewStatus: ReviewStatus
  image?: { src: string; origin: ImageOrigin }
}

export type ImportView = {
  id: string
  status: ImportStatus
  filesTotal: number
  audioTotal: number
  audioDone: number
  threads: number
  cardsCreated: number
  cardsNeedingReview: number
  errors: string[]
}

const SAFE_IMPORT_ERRORS = new Map([
  ['The chat import could not be processed.', 'pipeline_failed'],
  ['The chat date order could not be determined, so the import was not processed.', 'date_order_ambiguous'],
  ['One chat attachment could not be read, so it was kept without enrichment.', 'attachment_failed'],
  ['One chat thread could not be read, so it was skipped.', 'thread_failed'],
])

export function safeImportError(error: string) {
  return SAFE_IMPORT_ERRORS.get(error) ?? 'pipeline_failed'
}

export function filterCards(cards: KnowledgeCard[], applianceType: ApplianceType) {
  return applianceType === 'all' ? cards : cards.filter((card) => card.applianceType === applianceType)
}

export const dashboardFixture: { currentImport: ImportView; importHistory: ImportView[]; cards: KnowledgeCard[] } = {
  currentImport: {
    id: 'i_demo_current',
    status: 'extracting',
    filesTotal: 18,
    audioTotal: 14,
    audioDone: 14,
    threads: 9,
    cardsCreated: 7,
    cardsNeedingReview: 2,
    errors: [],
  },
  importHistory: (['queued', 'parsing', 'transcribing', 'extracting', 'done', 'failed'] as const).map((status, index) => ({
    id: `i_demo_${status}`,
    status,
    filesTotal: 18,
    audioTotal: 14,
    audioDone: status === 'queued' || status === 'parsing' ? 0 : Math.min(14, index * 4),
    threads: status === 'extracting' || status === 'done' ? 9 : 0,
    cardsCreated: status === 'done' ? 9 : 0,
    cardsNeedingReview: status === 'done' ? 2 : 0,
    errors: status === 'failed' ? ['The chat import could not be processed.'] : [],
  })),
  cards: [
    {
      id: 'fc_ac_1', applianceType: 'split_ac', applianceLabel: 'Split AC', brand: 'Voltas', code: 'E6',
      symptom: 'Indoor–outdoor communication fault; loose communication wire', source: 'Samyak · voice', confidence: null,
      reviewStatus: 'approved', image: { src: '/samples/display_e6.jpg', origin: 'public_post' },
    },
    {
      id: 'fc_ac_2', applianceType: 'split_ac', applianceLabel: 'Split AC', brand: 'Daikin', code: 'U4',
      symptom: 'Indoor–outdoor signal transmission error; wire 3 broken', source: 'Samyak', confidence: null,
      reviewStatus: 'approved',
    },
    {
      id: 'fc_washer_1', applianceType: 'washing_machine', applianceLabel: 'Washing machine', brand: 'LG', code: 'OE',
      symptom: 'Not draining; coin in the drain filter', source: 'Somil · plan', confidence: null,
      reviewStatus: 'approved',
    },
    {
      id: 'fc_review_1', applianceType: 'split_ac', applianceLabel: 'Split AC', brand: '', code: '',
      symptom: 'Maybe capacitor or motor', source: 'Somil · plan', confidence: null,
      reviewStatus: 'needs_review',
    },
    {
      id: 'fc_review_2', applianceType: 'unknown', applianceLabel: 'Appliance unclear', brand: '', code: '',
      symptom: 'Loose plug', source: 'Kaustubh · plan', confidence: null,
      reviewStatus: 'needs_review',
    },
  ],
}
