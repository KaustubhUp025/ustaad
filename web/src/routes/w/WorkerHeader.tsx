import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { UstaadLogo } from '@/components/brand/UstaadLogo'
import { cn } from '@/lib/utils'

// The worker app's one header: the logo always, a way home off Home, and a status slot on the right.
export function WorkerHeader({ back = false, children }: { back?: boolean; children?: ReactNode }) {
  const { t } = useTranslation()
  return (
    <header className="flex items-center gap-2 bg-graphite px-4 py-3 text-housing">
      {back && (
        <Link
          to="/w"
          aria-label={t('live.back')}
          className="-ml-2 flex size-(--touch) shrink-0 items-center justify-center rounded-sm outline-none focus-visible:ring-4 focus-visible:ring-primary"
        >
          <ArrowLeft aria-hidden className="size-6" />
        </Link>
      )}
      <UstaadLogo variant="lockup" on="dark" height={44} />
      <div className="ml-auto flex items-center gap-2">{children}</div>
    </header>
  )
}

// A dot and a word: green when Ustaad is reachable, yellow while it connects, red when it can't.
export function StatusPill({ state, label }: { state: 'ok' | 'pending' | 'error'; label: string }) {
  return (
    <span role="status" className="flex items-center gap-2 rounded-full border border-housing/25 px-3 py-1 text-[length:var(--text-sm)]">
      <span
        aria-hidden
        className={cn('size-2.5 rounded-full', state === 'ok' && 'bg-ok', state === 'pending' && 'bg-primary', state === 'error' && 'bg-destructive')}
      />
      {label}
    </span>
  )
}
