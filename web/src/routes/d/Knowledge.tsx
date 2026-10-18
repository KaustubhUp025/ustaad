import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { type ApplianceType, type FaultCard, useFaultCards } from '@/api/dashboard'
import { Button } from '@/components/ui/button'

const FILTERS: ApplianceType[] = ['all', 'split_ac', 'washing_machine']

export default function Knowledge() {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<ApplianceType>('all')
  const cards = useFaultCards(filter)

  if (cards.isLoading) return <DashboardState text={t('dashboard.loading')} />
  if (cards.isError) return <DashboardState text={t('dashboard.loadFailed')} error />

  const items = cards.data?.items ?? []
  const review = items.filter((card) => card.review_status === 'needs_review')
  return (
    <div className="mx-auto min-w-0 max-w-6xl">
      <header className="border-b border-border pb-5">
        <h1 className="font-heading text-[length:var(--text-xl)] font-bold">{t('dashboard.knowledge')}</h1>
        <p className="mt-1 max-w-2xl text-muted-foreground">{t('dashboard.knowledgeIntro')}</p>
      </header>
      <div className="flex flex-wrap gap-2 py-5" aria-label={t('dashboard.filterLabel')}>
        {FILTERS.map((value) => (
          <Button key={value} variant={filter === value ? 'default' : 'outline'} className="h-(--touch) px-4" onClick={() => setFilter(value)}>
            {t(`dashboard.filters.${value}`)}
          </Button>
        ))}
      </div>
      {items.length ? <CardList cards={items} /> : <DashboardState text={t('dashboard.knowledgeEmpty')} />}
      <section className="mt-10 border border-border border-t-4 border-t-parts bg-card" aria-labelledby="review-title">
        <div className="flex items-start justify-between gap-4 px-4 py-4">
          <div>
            <h2 id="review-title" className="font-heading text-[length:var(--text-lg)] font-bold">{t('dashboard.reviewQueue')}</h2>
            <p className="text-muted-foreground">{t('dashboard.reviewIntro')}</p>
          </div>
          <span className="rounded-sm bg-background px-3 py-2 font-heading text-[length:var(--text-lg)] font-bold tabular-nums">{review.length}</span>
        </div>
        {review.length ? (
          <ul className="divide-y divide-border">
            {review.map((card) => <li key={card.id} className="px-4 py-4"><CardSummary card={card} /></li>)}
          </ul>
        ) : <p className="px-4 pb-4 text-muted-foreground">{t('dashboard.reviewEmpty')}</p>}
      </section>
    </div>
  )
}

function CardList({ cards }: { cards: FaultCard[] }) {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="cards-title">
      <h2 id="cards-title" className="sr-only">{t('dashboard.faultCards')}</h2>
      <div className="hidden grid-cols-[130px_100px_minmax(220px,1fr)_180px_100px] gap-4 border-y border-border px-3 py-2 text-[length:var(--text-sm)] text-muted-foreground md:grid">
        <span>{t('dashboard.appliance')}</span><span>{t('dashboard.code')}</span><span>{t('dashboard.symptom')}</span><span>{t('dashboard.source')}</span><span>{t('dashboard.confidence')}</span>
      </div>
      <ul className="divide-y divide-border border-b border-border">{cards.map((card) => <CardRow card={card} key={card.id} />)}</ul>
    </section>
  )
}

function CardRow({ card }: { card: FaultCard }) {
  const { t } = useTranslation()
  return (
    <li className="grid min-w-0 gap-3 px-3 py-4 md:grid-cols-[130px_100px_minmax(220px,1fr)_180px_100px] md:items-center">
      <span className="font-semibold">{card.appliance_type ? t(`dashboard.filters.${card.appliance_type}`) : t('dashboard.filters.unknown')}</span>
      <span className="font-heading text-[length:var(--text-lg)] font-bold">{card.error_code || '—'}</span>
      <CardSummary card={card} compact />
      <span className="text-[length:var(--text-sm)] text-muted-foreground">{card.source.author || card.source.doc || t('dashboard.sourceUnknown')}</span>
      <span className="font-heading tabular-nums">{Math.round(card.confidence * 100)}%</span>
    </li>
  )
}

function CardSummary({ card, compact = false }: { card: FaultCard; compact?: boolean }) {
  return (
    <div className="min-w-0">
      <p>{card.symptom}</p>
      {!compact ? <p className="mt-1 text-[length:var(--text-sm)] text-muted-foreground">{card.brand || '—'} · {card.error_code || '—'}</p> : null}
    </div>
  )
}

function DashboardState({ text, error = false }: { text: string; error?: boolean }) {
  return <p role={error ? 'alert' : 'status'} className={`mx-auto min-w-0 max-w-6xl py-10 ${error ? 'text-destructive' : 'text-muted-foreground'}`}>{text}</p>
}
