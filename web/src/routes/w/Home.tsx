import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useHealth } from '@/api/health'
import { Button } from '@/components/ui/button'

export default function Home() {
  const { t } = useTranslation()
  const health = useHealth()

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="bg-graphite px-4 py-4 text-housing">
        <h1 className="font-heading text-[length:var(--text-xl)] font-bold">Ustaad</h1>
      </header>
      <section className="flex flex-col items-start gap-4 px-4 py-6">
        <p className="text-[length:var(--text-caption)]">{t('app.tagline')}</p>
        <div
          role="status"
          className="w-full rounded-sm border-l-4 bg-card px-4 py-3 data-[state=error]:border-l-destructive data-[state=ok]:border-l-ok"
          data-state={health.isPending ? 'checking' : health.isSuccess ? 'ok' : 'error'}
        >
          {health.isPending ? t('health.checking') : health.isSuccess ? t('health.ok') : t('health.error')}
        </div>
        {health.isError && (
          <Button className="h-(--touch) px-6 text-[length:var(--text-body)]" onClick={() => health.refetch()}>
            {t('health.retry')}
          </Button>
        )}
        <Button asChild variant="outline" className="h-(--touch) px-6 text-[length:var(--text-body)]">
          <Link to="/w/stock">{t('stock.open')}</Link>
        </Button>
      </section>
    </main>
  )
}
