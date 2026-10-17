import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useHealth } from '@/api/health'
import { startDemo } from '@/api/session'
import { Button } from '@/components/ui/button'

export default function Home() {
  const { t } = useTranslation()
  const health = useHealth()
  const navigate = useNavigate()
  const [demo, setDemo] = useState<'idle' | 'starting' | 'failed'>('idle')

  // No login: a demo session for the seeded worker, then a new job in the language picked here. English comes first
  // so a judge who speaks no Hindi can follow; Ustaad still cites the senior's Hindi voice note (phone test, Oct 17).
  const tryDemo = async (lang: 'en' | 'hi') => {
    setDemo('starting')
    try {
      await startDemo()
      navigate(`/w/job/j_${crypto.randomUUID().slice(0, 8)}?lang=${lang}`)
    } catch {
      setDemo('failed')
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col">
      <header className="bg-graphite px-4 py-4 text-housing">
        <h1 className="font-heading text-[length:var(--text-xl)] font-bold">Ustaad</h1>
      </header>
      <section className="flex flex-col items-start gap-4 px-4 py-6">
        <p className="text-[length:var(--text-caption)]">{t('app.tagline')}</p>
        <Button
          className="h-(--touch) w-full text-[length:var(--text-body)]"
          disabled={demo === 'starting'}
          onClick={() => void tryDemo('en')}
        >
          {demo === 'starting' ? t('demo.starting') : t('demo.tryEn')}
        </Button>
        <Button
          variant="outline"
          lang="hi"
          className="h-(--touch) w-full text-[length:var(--text-body)]"
          disabled={demo === 'starting'}
          onClick={() => void tryDemo('hi')}
        >
          {t('demo.tryHi')}
        </Button>
        {demo === 'failed' && (
          <p role="alert" className="border-l-4 border-l-destructive pl-3">
            {t('demo.failed')}
          </p>
        )}
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
