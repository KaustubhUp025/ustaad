export type ImportStatus = 'queued' | 'parsing' | 'transcribing' | 'extracting' | 'done' | 'failed'
export type ApplianceType = 'all' | 'split_ac' | 'washing_machine' | 'fridge'
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
  confidence: number
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

const SAFE_IMPORT_ERRORS = new Set(['pipeline_failed', 'archive_invalid', 'date_order_ambiguous'])

export function safeImportError(error: string) {
  return SAFE_IMPORT_ERRORS.has(error) ? error : 'pipeline_failed'
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
    errors: status === 'failed' ? ['pipeline_failed'] : [],
  })),
  cards: [
    {
      id: 'fc_ac_1', applianceType: 'split_ac', applianceLabel: 'Split AC', brand: 'Voltas', code: 'E6',
      symptom: 'Indoor unit stops after three minutes', source: 'Ramesh · May 2025', confidence: 0.94,
      reviewStatus: 'approved', image: { src: '/samples/display_e6.jpg', origin: 'public_post' },
    },
    {
      id: 'fc_ac_2', applianceType: 'split_ac', applianceLabel: 'Split AC', brand: 'LG', code: 'CH38',
      symptom: 'Cooling drops after restart', source: 'Amit · June 2025', confidence: 0.58,
      reviewStatus: 'needs_review', image: { src: '/samples/voltas_label.jpg', origin: 'ai_generated' },
    },
    {
      id: 'fc_washer_1', applianceType: 'washing_machine', applianceLabel: 'Washing machine', brand: 'Samsung', code: '4C',
      symptom: 'Water does not enter the drum', source: 'Demo import · July 2025', confidence: 0.87,
      reviewStatus: 'approved',
    },
    {
      id: 'fc_fridge_1', applianceType: 'fridge', applianceLabel: 'Fridge', brand: 'Whirlpool', code: '—',
      symptom: 'Compressor clicks and stops', source: 'Demo import · July 2025', confidence: 0.52,
      reviewStatus: 'needs_review',
    },
  ],
}
