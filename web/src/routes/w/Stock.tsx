import { Minus, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { type InventoryItem, useInventory, useStockStep } from '@/api/inventory'
import { Button } from '@/components/ui/button'

export default function Stock() {
  const { t } = useTranslation()
  const inventory = useInventory()
  const step = useStockStep()
  const items = inventory.data?.items ?? []

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-housing/20 bg-graphite px-4 py-4 text-housing">
        <h1 className="font-heading text-[length:var(--text-xl)] font-bold">{t('stock.title')}</h1>
        <span className="rounded-sm border border-housing/50 px-2 py-1 text-[length:var(--text-sm)]">{t('stock.demo')}</span>
      </header>
      {inventory.isPending && (
        <p role="status" className="mx-4 mt-6 border-l-4 border-l-primary bg-card px-4 py-3">
          {t('stock.loading')}
        </p>
      )}
      {inventory.isError && (
        <div role="alert" className="mx-4 mt-6 flex flex-col items-start gap-4 border-l-4 border-l-destructive bg-card px-4 py-4">
          <p>{t('stock.error')}</p>
          <Button className="h-(--touch) px-6 text-[length:var(--text-body)]" onClick={() => inventory.refetch()}>
            {t('stock.retry')}
          </Button>
        </div>
      )}
      {inventory.isSuccess && items.length === 0 && <p className="mx-4 mt-6 border-l-4 border-l-primary bg-card px-4 py-4">{t('stock.empty')}</p>}
      {step.isError && (
        <p role="alert" className="mx-4 mt-4 border-l-4 border-l-parts bg-card px-4 py-3">
          {t('stock.saveFailed')}
        </p>
      )}
      <ul className="mx-4 mt-6 border-y border-border">
        {items.map((item) => (
          <Row key={item.id} item={item} busy={step.isPending} onStep={(delta) => step.mutate({ part: item.name, delta })} />
        ))}
      </ul>
    </main>
  )
}

function Row({ item, busy, onStep }: { item: InventoryItem; busy: boolean; onStep: (delta: 1 | -1) => void }) {
  const { t } = useTranslation()
  const low = item.qty <= item.min_qty

  return (
    <li className="flex items-center gap-3 px-2 py-4 sm:px-4">
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
        <span className="break-words font-heading text-[length:var(--text-caption)] font-semibold">{item.name}</span>
        {low && (
          <span className="rounded-sm border border-parts px-2 text-[length:var(--text-sm)] text-parts">
            {item.qty === 0 ? t('stock.out') : t('stock.low')}
          </span>
        )}
      </div>
      <Button
        variant="outline"
        className="size-(--touch)"
        disabled={busy || item.qty === 0}
        aria-label={t('stock.less', { name: item.name })}
        onClick={() => onStep(-1)}
      >
        <Minus />
      </Button>
      <span
        className="min-w-10 text-center font-heading text-[length:var(--text-lg)] font-bold tabular-nums"
        aria-label={t('stock.inStock', { qty: item.qty })}
      >
        {item.qty}
      </span>
      <Button
        variant="outline"
        className="size-(--touch)"
        disabled={busy}
        aria-label={t('stock.more', { name: item.name })}
        onClick={() => onStep(1)}
      >
        <Plus />
      </Button>
    </li>
  )
}
