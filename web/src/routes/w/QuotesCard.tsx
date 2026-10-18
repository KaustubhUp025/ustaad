import { Check, Mic } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useApproveQuote, useQuotes } from '@/api/quotes'
import type { QuoteItem } from '@/audio/liveClient'
import { Button } from '@/components/ui/button'

import { initialQuoteRows, rankedQuoteRows } from './quotesView'

type Props = { quoteRequestId: string | null; initialItems: QuoteItem[] }

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

// This remains deliberately small: the socket gives the immediate vendor list, then REST supplies ranked replies.
export function QuotesCard({ quoteRequestId, initialItems }: Props) {
  const { t } = useTranslation()
  const query = useQuotes(quoteRequestId)
  const approve = useApproveQuote(quoteRequestId)
  const [approvedId, setApprovedId] = useState<string | null>(null)

  if (!quoteRequestId) return null

  const response = query.data
  const rows = response
    ? rankedQuoteRows(response.quotes, response.request.approved_quote_id, response.request.status === 'open')
    : initialQuoteRows(initialItems)
  const waiting = query.isPending || rows.length === 0 || rows.some((row) => row.available === null)

  return (
    <section aria-labelledby="quotes-title" className="mx-4 mb-4 border border-border border-l-4 border-l-parts bg-card px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 id="quotes-title" className="font-heading text-[length:var(--text-lg)] font-bold">
          {t('quotes.title')}
        </h2>
        {waiting && <p role="status" className="rounded-sm bg-background px-2 py-1 text-[length:var(--text-sm)] text-muted-foreground">{t('quotes.waiting')}</p>}
      </div>

      {query.isError && (
        <div role="alert" className="mt-3 flex flex-col items-start gap-3 border-l-4 border-destructive bg-background p-3 text-[length:var(--text-body)]">
          <p>{t('quotes.loadFailed')}</p>
          <Button variant="outline" className="h-(--touch) px-6" onClick={() => void query.refetch()}>
            {t('live.retry')}
          </Button>
        </div>
      )}

      <ul className="mt-3 space-y-3">
        {rows.map((row) => (
          <li key={row.id} className="border-l-4 border-parts bg-background px-3 py-3">
            <div className="flex items-start justify-between gap-3">
              <p className="min-w-0 font-semibold">{row.vendor}</p>
              {row.fromVoice && (
                <span className="inline-flex items-center gap-1 rounded-sm bg-secondary px-2 py-1 text-[length:var(--text-sm)]">
                  <Mic aria-hidden className="size-4" /> {t('quotes.voiceReply')}
                </span>
              )}
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[length:var(--text-sm)]">
              <div><dt className="sr-only">{t('quotes.availability')}</dt><dd>{row.available === true ? t('quotes.available') : row.available === false ? t('quotes.unavailable') : t('quotes.replyPending')}</dd></div>
              <div><dt className="sr-only">{t('quotes.price')}</dt><dd className="font-semibold text-parts">{row.priceInr === null ? t('quotes.pricePending') : inr.format(row.priceInr)}</dd></div>
              <div><dt className="sr-only">{t('quotes.eta')}</dt><dd>{row.eta ?? t('quotes.etaPending')}</dd></div>
              {row.distanceKm !== null && <div><dt className="sr-only">{t('quotes.distance')}</dt><dd>{t('quotes.distanceValue', { distance: row.distanceKm })}</dd></div>}
            </dl>
            {row.approved || approvedId === row.id ? (
              <p role="status" className="mt-3 inline-flex items-center gap-1 font-semibold text-ok"><Check aria-hidden className="size-4" /> {t('quotes.approved')}</p>
            ) : row.eligible ? (
              <Button
                className="mt-3 h-(--touch) w-full text-[length:var(--text-body)]"
                disabled={approve.isPending}
                onClick={() => approve.mutate(row.id, { onSuccess: () => setApprovedId(row.id) })}
              >
                {t('quotes.approve')}
              </Button>
            ) : null}
          </li>
        ))}
      </ul>

      {approve.isError && <p role="alert" className="mt-3 border-l-4 border-destructive bg-background px-3 py-2 text-[length:var(--text-body)] text-destructive">{t('quotes.approvalFailed')}</p>}
    </section>
  )
}
