import { Minus, Package, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { type InventoryItem, useInventory, useStockStep } from '@/api/inventory'
import { Button } from '@/components/ui/button'

import { WorkerHeader } from './WorkerHeader'

export default function Stock() {
  const { t } = useTranslation()
  const inventory = useInventory()
  const step = useStockStep()
  const items = inventory.data?.items ?? []

  return (
    <main className="flex min-h-dvh flex-col bg-background">
      <WorkerHeader back />
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-5 px-4 py-6">
        <section className="flex flex-col gap-2">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h1 className="font-heading text-[length:var(--text-xl)] font-bold">{t('stock.title')}</h1>
            {/* A label, not a button: the counts below are seeded for the demo. */}
            <span className="text-[length:var(--text-sm)] text-parts">{t('stock.demo')}</span>
          </div>
          <p className="text-muted-foreground">{t('stock.intro')}</p>
        </section>

        {inventory.isPending && (
          <p role="status" className="text-muted-foreground">
            {t('stock.loading')}
          </p>
        )}
        {inventory.isError && (
          <div role="alert" className="flex flex-col items-start gap-4 rounded-lg border border-destructive px-4 py-4">
            <p>{t('stock.error')}</p>
            <Button className="h-(--touch) px-6 text-[length:var(--text-body)]" onClick={() => inventory.refetch()}>
              {t('stock.retry')}
            </Button>
          </div>
        )}
        {inventory.isSuccess && items.length === 0 && (
          <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed border-border px-6 py-10 text-center">
            <Package aria-hidden className="size-12 text-parts" />
            <p className="text-[length:var(--text-caption)]">{t('stock.empty')}</p>
            <Button asChild className="h-(--touch) px-6 text-[length:var(--text-body)]">
              <Link to="/w">{t('stock.back')}</Link>
            </Button>
          </div>
        )}
        {step.isError && (
          <p role="alert" className="rounded-lg border border-parts px-4 py-3">
            {t('stock.saveFailed')}
          </p>
        )}
        {items.length > 0 && (
          <>
            <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
              {items.map((item) => (
                <Row key={item.id} item={item} busy={step.isPending} onStep={(delta) => step.mutate({ part: item.name, delta })} />
              ))}
            </ul>
            <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('stock.howTo')}</p>
            <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('stock.order')}</p>
          </>
        )}
      </div>
    </main>
  )
}

function Row({ item, busy, onStep }: { item: InventoryItem; busy: boolean; onStep: (delta: 1 | -1) => void }) {
  const { t } = useTranslation()
  const low = item.qty <= item.min_qty

  return (
    <li className="flex items-center gap-3 px-4 py-4">
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
