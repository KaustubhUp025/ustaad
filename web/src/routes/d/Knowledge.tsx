import { Check, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { type ApplianceType, dashboardFixture, filterCards, type KnowledgeCard } from '@/api/dashboard'
import { Button } from '@/components/ui/button'

const FILTERS: ApplianceType[] = ['all', 'split_ac', 'washing_machine']

export default function Knowledge() {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<ApplianceType>('all')
  const [cards, setCards] = useState(dashboardFixture.cards)
  const visible = useMemo(() => filterCards(cards, filter), [cards, filter])
  const review = cards.filter((card) => card.reviewStatus === 'needs_review')
  const decide = (id: string, approved: boolean) =>
    setCards((current) => approved ? current.map((card) => card.id === id ? { ...card, reviewStatus: 'approved' } : card) : current.filter((card) => card.id !== id))

  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div><h1 className="font-heading text-[length:var(--text-xl)] font-bold">{t('dashboard.knowledge')}</h1><p className="mt-1 text-muted-foreground">{t('dashboard.knowledgeIntro')}</p></div>
        <span className="rounded-sm border border-parts px-2 py-1 text-[length:var(--text-sm)] text-parts">{t('dashboard.synthetic')}</span>
      </header>
      <div className="flex gap-2 overflow-x-auto py-5" aria-label={t('dashboard.filterLabel')}>
        {FILTERS.map((value) => <Button key={value} variant={filter === value ? 'default' : 'outline'} className="h-(--touch) shrink-0" onClick={() => setFilter(value)}>{t(`dashboard.filters.${value}`)}</Button>)}
      </div>
      <section aria-labelledby="cards-title">
        <h2 id="cards-title" className="sr-only">{t('dashboard.faultCards')}</h2>
        <div className="hidden grid-cols-[130px_100px_minmax(220px,1fr)_180px_100px] gap-4 border-y border-border px-3 py-2 text-[length:var(--text-sm)] text-muted-foreground md:grid">
          <span>{t('dashboard.appliance')}</span><span>{t('dashboard.code')}</span><span>{t('dashboard.symptom')}</span><span>{t('dashboard.source')}</span><span>{t('dashboard.confidence')}</span>
        </div>
        <ul className="divide-y divide-border border-b border-border">{visible.map((card) => <CardRow card={card} key={card.id} />)}</ul>
      </section>
      <section className="mt-10 border-t-4 border-t-parts bg-card" aria-labelledby="review-title">
        <div className="flex items-center justify-between px-4 py-4"><div><h2 id="review-title" className="font-heading text-[length:var(--text-lg)] font-bold">{t('dashboard.reviewQueue')}</h2><p className="text-muted-foreground">{t('dashboard.reviewIntro')}</p></div><span className="font-heading text-[length:var(--text-lg)] font-bold tabular-nums">{review.length}</span></div>
        <ul className="divide-y divide-border">{review.map((card) => <li key={card.id} className="grid gap-4 px-4 py-4 md:grid-cols-[1fr_auto] md:items-center"><CardSummary card={card} /><div className="flex gap-2"><Button className="h-(--touch)" onClick={() => decide(card.id, true)}><Check />{t('dashboard.approve')}</Button><Button variant="outline" className="h-(--touch)" onClick={() => decide(card.id, false)}><X />{t('dashboard.reject')}</Button></div></li>)}</ul>
      </section>
    </div>
  )
}

function CardRow({ card }: { card: KnowledgeCard }) {
  const { t } = useTranslation()
  return <li className="grid gap-3 px-3 py-4 md:grid-cols-[130px_100px_minmax(220px,1fr)_180px_100px] md:items-center"><span className="font-semibold">{card.applianceLabel}</span><span className="font-heading text-[length:var(--text-lg)] font-bold">{card.code || '—'}</span><CardSummary card={card} compact /><span className="text-[length:var(--text-sm)] text-muted-foreground">{card.source}</span><span className="font-heading tabular-nums">{card.confidence === null ? t('dashboard.notScored') : `${Math.round(card.confidence * 100)}%`}</span>{card.image && <figure className="md:col-start-3"><img className="h-24 w-40 rounded-sm border border-border object-cover" src={card.image.src} alt="" /><figcaption className="mt-1 text-[length:var(--text-sm)] text-muted-foreground">{t(`dashboard.image.${card.image.origin}`)}</figcaption></figure>}</li>
}

function CardSummary({ card, compact = false }: { card: KnowledgeCard; compact?: boolean }) {
  return <div className="min-w-0"><p>{card.symptom}</p>{!compact && <p className="mt-1 text-[length:var(--text-sm)] text-muted-foreground">{card.brand || '—'} · {card.code || '—'}</p>}</div>
}
