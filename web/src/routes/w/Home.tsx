import { BookOpen, ChevronRight, MessageCircle, Mic, Package, UserRound } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useHealth } from '@/api/health'
import { startDemo } from '@/api/session'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { StatusPill, WorkerHeader } from './WorkerHeader'

type Lang = 'hi' | 'te' | 'ta' | 'bn' | 'en'
const LANGS: Lang[] = ['hi', 'te', 'ta', 'bn', 'en']

export default function Home() {
  const { t } = useTranslation()
  const health = useHealth()
  const navigate = useNavigate()
  const [demo, setDemo] = useState<'idle' | 'starting' | 'failed'>('idle')
  const [picking, setPicking] = useState(false)

  // No login: a demo session for the seeded worker, then a new job in the language picked here. English comes first
  // so a judge who speaks no Hindi can follow; Ustaad still cites the senior's Hindi voice note (phone test, Oct 17).
  // "Set up a profile" starts the onboarding interview (G1) on a new, empty demo worker in the language he picks.
  const tryDemo = async (lang: Lang, onboarding = false) => {
    setDemo('starting')
    try {
      await startDemo(onboarding ? { onboarding, lang } : undefined)
      navigate(`/w/job/j_${crypto.randomUUID().slice(0, 8)}?lang=${lang}${onboarding ? '&onboarding=1' : ''}`)
    } catch {
      setDemo('failed')
    }
  }
  const starting = demo === 'starting'

  return (
    <main className="flex min-h-dvh flex-col bg-background">
      <WorkerHeader>
        <StatusPill
          state={health.isPending ? 'pending' : health.isSuccess ? 'ok' : 'error'}
          label={t(health.isPending ? 'health.checking' : health.isSuccess ? 'health.live' : 'health.offline')}
        />
      </WorkerHeader>

      <div className="mx-auto grid w-full max-w-5xl flex-1 lg:grid-cols-2 lg:gap-10 lg:px-6 lg:py-10">
        {/* The hero carries the header's graphite down, so the first screen is one block: what it is, then start. */}
        <section className="flex flex-col gap-5 bg-graphite px-4 pt-4 pb-8 text-housing lg:self-start lg:rounded-lg lg:p-8">
          <h1 className="font-heading text-[length:var(--text-xl)] leading-tight font-bold">{t('app.tagline')}</h1>
          <p className="text-[length:var(--text-body)] text-housing/85">{t('home.intro')}</p>
          <div className="flex flex-col gap-3">
            <Button className="h-14 w-full gap-3 text-[length:var(--text-body)] font-semibold" disabled={starting} onClick={() => void tryDemo('en')}>
              <Mic aria-hidden className="size-6" />
              {starting ? t('demo.starting') : t('demo.tryEn')}
            </Button>
            <Button
              variant="outline"
              lang="hi"
              className="h-14 w-full border-housing/40 bg-transparent text-[length:var(--text-body)] text-housing hover:bg-housing/10 hover:text-housing"
              disabled={starting}
              onClick={() => void tryDemo('hi')}
            >
              {t('demo.tryHi')}
            </Button>
            {/* G6: the same repair demo in Telugu. */}
            <Button
              variant="outline"
              lang="te"
              className="h-14 w-full border-housing/40 bg-transparent text-[length:var(--text-body)] text-housing hover:bg-housing/10 hover:text-housing"
              disabled={starting}
              onClick={() => void tryDemo('te')}
            >
              {t('demo.tryTe')}
            </Button>
          </div>
          {demo === 'failed' && (
            <p role="alert" className="rounded-sm bg-destructive px-3 py-2 text-housing">
              {t('demo.failed')}
            </p>
          )}
          {health.isError && (
            <div role="alert" className="flex flex-wrap items-center gap-3 text-[length:var(--text-sm)]">
              <span>{t('health.error')}</span>
              <Button variant="outline" className="h-(--touch) border-housing/40 bg-transparent px-4 text-housing" onClick={() => health.refetch()}>
                {t('health.retry')}
              </Button>
            </div>
          )}
          <figure className="mt-1 border-l-2 border-primary pl-4">
            <figcaption className="text-[length:var(--text-sm)] text-housing/75">{t('home.trySaying')}</figcaption>
            <blockquote lang="hi" className="text-[length:var(--text-caption)]">“{t('live.ex1')}”</blockquote>
          </figure>
          {/* Wide screens have the room to show what the job screen shows first: the code read from his photo. */}
          <div aria-hidden className="hidden items-center gap-4 rounded-sm border border-housing/15 px-5 py-4 lg:flex">
            <span className="font-code text-[length:var(--text-code)] leading-none text-led">E6</span>
            <span>
              <span className="block font-heading text-[length:var(--text-lg)] font-bold">Voltas</span>
              <span className="block text-[length:var(--text-sm)] text-housing/75">{t('live.seen')}</span>
            </span>
          </div>
        </section>

        <div className="flex flex-col gap-8 px-4 py-8 lg:px-0 lg:py-0">
          <section aria-labelledby="how">
            <h2 id="how" className="mb-4 font-heading text-[length:var(--text-lg)] font-bold">
              {t('home.howTitle')}
            </h2>
            {/* A real sequence, so it is numbered: ask, show, fix. */}
            <ol className="flex flex-col gap-4">
              {(['1', '2', '3'] as const).map((n) => (
                <li key={n} className="flex gap-4">
                  <span aria-hidden className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary font-heading font-bold text-primary-foreground">
                    {n}
                  </span>
                  <div>
                    <p className="font-semibold">{t(`home.how${n}Title`)}</p>
                    <p className="text-muted-foreground">{t(`home.how${n}`)}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="more">
            <h2 id="more" className="mb-3 font-heading text-[length:var(--text-lg)] font-bold">
              {t('home.moreTitle')}
            </h2>
            <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
              {/* First: setting up a profile makes him a worker of his own, in the language he picks. */}
              <li>
                <button
                  type="button"
                  aria-expanded={picking}
                  disabled={starting}
                  onClick={() => setPicking(!picking)}
                  className="flex min-h-16 w-full items-center gap-4 px-4 py-3 text-left outline-none hover:bg-muted focus-visible:ring-4 focus-visible:ring-ring focus-visible:ring-inset disabled:opacity-50"
                >
                  <Icon tone="ink">
                    <UserRound className="size-6" />
                  </Icon>
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold">{t('onboard.setup')}</span>
                    <span className="block text-[length:var(--text-sm)] text-muted-foreground">{t('home.profileText')}</span>
                  </span>
                  <ChevronRight aria-hidden className={cn('size-5 text-muted-foreground transition-transform', picking && 'rotate-90')} />
                </button>
                {picking && (
                  <fieldset className="px-4 pb-4">
                    <legend className="mb-2 px-4 text-[length:var(--text-sm)] text-muted-foreground">{t('onboard.pickLanguage')}</legend>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {LANGS.map((lang) => (
                        <Button
                          key={lang}
                          variant="outline"
                          lang={lang}
                          className="h-(--touch) text-[length:var(--text-body)]"
                          disabled={starting}
                          onClick={() => void tryDemo(lang, true)}
                        >
                          {t(`languages.${lang}`)}
                        </Button>
                      ))}
                    </div>
                  </fieldset>
                )}
              </li>
              <Row to="/d/import" icon={<MessageCircle className="size-6" />} tone="ok" title={t('home.importTitle')} text={t('home.importText')} />
              <Row to="/w/stock" icon={<Package className="size-6" />} tone="parts" title={t('stock.title')} text={t('home.stockText')} />
              <Row to="/d/knowledge" icon={<BookOpen className="size-6" />} tone="ink" title={t('home.cardsTitle')} text={t('home.cardsText')} />
            </ul>
          </section>

          <p className="text-[length:var(--text-sm)] text-muted-foreground">{t('home.honest')}</p>
        </div>
      </div>
    </main>
  )
}

type Tone = 'ok' | 'parts' | 'ink'

function Icon({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      aria-hidden
      className={cn(
        'flex size-11 shrink-0 items-center justify-center rounded-full',
        tone === 'ok' && 'bg-ok text-housing',
        tone === 'parts' && 'bg-parts text-housing',
        tone === 'ink' && 'bg-foreground text-background',
      )}
    >
      {children}
    </span>
  )
}

function Row({ to, icon, tone, title, text }: { to: string; icon: ReactNode; tone: Tone; title: string; text: string }) {
  return (
    <li>
      <Link
        to={to}
        className="flex min-h-16 items-center gap-4 px-4 py-3 outline-none hover:bg-muted focus-visible:ring-4 focus-visible:ring-ring focus-visible:ring-inset"
      >
        <Icon tone={tone}>{icon}</Icon>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold">{title}</span>
          <span className="block text-[length:var(--text-sm)] text-muted-foreground">{text}</span>
        </span>
        <ChevronRight aria-hidden className="size-5 text-muted-foreground" />
      </Link>
    </li>
  )
}
