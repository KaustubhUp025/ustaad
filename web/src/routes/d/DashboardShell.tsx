import { BookOpen, Upload } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'

import { UstaadLogo } from '@/components/brand/UstaadLogo'

export default function DashboardShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-(--touch) min-w-0 items-center gap-3 border-l-4 px-4 py-3 outline-none focus-visible:ring-4 focus-visible:ring-ring ${isActive ? 'border-l-primary bg-card font-semibold' : 'border-l-transparent text-muted-foreground hover:bg-card'}`

  return (
    <div className="min-h-dvh bg-background text-foreground lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-border bg-graphite text-housing lg:min-h-dvh lg:border-r lg:border-b-0 lg:border-r-border">
        <div className="border-b border-housing/20 px-5 py-5">
          <UstaadLogo variant="lockup" on="dark" height={36} />
          <p className="mt-1 text-[length:var(--text-sm)] text-housing/80">{t('dashboard.subtitle')}</p>
        </div>
        <nav aria-label={t('dashboard.navigation')} className="grid grid-cols-2 lg:grid-cols-1">
          <NavLink to="/d/knowledge" className={navClass}><BookOpen className="shrink-0" size={20} />{t('dashboard.knowledge')}</NavLink>
          <NavLink to="/d/import" className={navClass}><Upload className="shrink-0" size={20} />{t('dashboard.import')}</NavLink>
        </nav>
      </aside>
      <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">{children}</main>
    </div>
  )
}
