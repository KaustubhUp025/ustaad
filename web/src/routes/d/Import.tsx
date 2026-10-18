import { AlertTriangle, Check, FileArchive, LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { dashboardFixture, type ImportStatus, safeImportError } from '@/api/dashboard'

const STEPS: ImportStatus[] = ['queued', 'parsing', 'transcribing', 'extracting', 'done']

export default function ImportDashboard() {
  const { t } = useTranslation()
  const current = dashboardFixture.currentImport
  const currentIndex = STEPS.indexOf(current.status)

  return (
    <div className="mx-auto min-w-0 max-w-5xl">
      <header className="border-b border-border pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-heading text-[length:var(--text-xl)] font-bold">{t('dashboard.import')}</h1>
          <span className="rounded-sm border border-parts px-2 py-1 text-[length:var(--text-sm)] text-parts">
            {t('dashboard.synthetic')}
          </span>
        </div>
        <p className="mt-2 max-w-3xl text-muted-foreground">{t('dashboard.importDisclosure')}</p>
      </header>

      <section className="mt-6 border border-border border-l-4 border-l-primary bg-card p-5" aria-labelledby="progress-title">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="progress-title" className="font-heading text-[length:var(--text-lg)] font-bold">
              {t('dashboard.importProgress')}
            </h2>
            <p role="status" className="mt-1">{t(`dashboard.status.${current.status}`)}</p>
          </div>
          <span className="rounded-sm bg-background px-3 py-2 font-heading text-[length:var(--text-xl)] font-bold tabular-nums">
            {current.cardsCreated}
          </span>
        </div>

        <ol className="mt-6 grid gap-2 sm:grid-cols-5">
          {STEPS.map((step, index) => (
            <li
              key={step}
              className={`border-t-4 bg-background px-2 pt-2 text-[length:var(--text-sm)] ${index <= currentIndex ? 'border-t-ok' : 'border-t-border text-muted-foreground'}`}
            >
              {index < currentIndex ? (
                <Check className="mb-1" size={18} />
              ) : index === currentIndex ? (
                <LoaderCircle className="mb-1 motion-safe:animate-spin" size={18} />
              ) : null}
              {t(`dashboard.status.${step}`)}
            </li>
          ))}
        </ol>

        <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
          <Metric label={t('dashboard.voiceNotes')} value={`${current.audioDone}/${current.audioTotal}`} />
          <Metric label={t('dashboard.threads')} value={current.threads} />
          <Metric label={t('dashboard.cardsCreated')} value={current.cardsCreated} />
          <Metric label={t('dashboard.needsReview')} value={current.cardsNeedingReview} />
        </dl>
      </section>

      <section className="mt-8" aria-labelledby="activity-title">
        <h2 id="activity-title" className="font-heading text-[length:var(--text-lg)] font-bold">
          {t('dashboard.importActivity')}
        </h2>
        <ul className="mt-3 border-y border-border">
          {dashboardFixture.importHistory.map((item, index) => (
            <li
              key={item.id}
              className="grid grid-cols-[32px_minmax(0,1fr)] items-center gap-3 border-b border-border px-2 py-4 last:border-b-0 sm:grid-cols-[32px_minmax(0,1fr)_auto]"
            >
              <FileArchive className="shrink-0 text-parts" size={22} />
              <div>
                <p className="font-semibold">{t('dashboard.importItem', { number: index + 1 })}</p>
                <p className="text-[length:var(--text-sm)] text-muted-foreground">
                  {t(`dashboard.status.${item.status}`)}
                </p>
                {item.errors.map((error) => (
                  <p
                    role="alert"
                    className="mt-1 flex items-center gap-1 text-[length:var(--text-sm)] text-destructive"
                    key={error}
                  >
                    <AlertTriangle size={16} />
                    {t(`dashboard.errors.${safeImportError(error)}`)}
                  </p>
                ))}
              </div>
              {item.cardsCreated > 0 && (
                <span className="col-start-2 justify-self-start rounded-sm border border-ok px-2 py-1 text-[length:var(--text-sm)] text-ok sm:col-start-auto">
                  {t('dashboard.cardsCreatedBadge', { count: item.cardsCreated })}
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-[length:var(--text-sm)] text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-heading text-[length:var(--text-lg)] font-bold tabular-nums">{value}</dd>
    </div>
  )
}
