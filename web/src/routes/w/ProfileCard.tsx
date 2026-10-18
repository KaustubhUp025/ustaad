import { Check, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { ProfileView } from '@/audio/profile'

// The onboarding profile card (T21, G1): fills in as each answer is saved; appliances show as chips. Once onboarding is
// done it folds to one line he can open, so the repair talk and the mic stay on screen (phone test, Oct 18).
export function ProfileCard({ profile }: { profile: ProfileView }) {
  const { t } = useTranslation()
  const rows: [string, React.ReactNode][] = []
  if (profile.trades)
    rows.push([
      t('profile.trades'),
      <ul className="flex flex-wrap gap-2">
        {profile.trades.map((trade) => (
          <li key={trade} className="rounded-sm border border-ok px-2 py-1 text-[length:var(--text-sm)]">
            {t(`trade.${trade}`)}
          </li>
        ))}
      </ul>,
    ])
  if (profile.brands) rows.push([t('profile.brands'), profile.brands.join(', ')])
  if (profile.pincode) rows.push([t('profile.pincode'), profile.pincode])
  if (profile.experience_yrs !== undefined)
    rows.push([t('profile.experience'), t('profile.years', { count: profile.experience_yrs })])
  if (profile.stock)
    rows.push([
      t('profile.stock'),
      profile.stock
        .map(({ part, qty }) => (qty === 0 ? `${part} (${t('profile.notKept')})` : qty ? `${part} (${t('profile.pieces', { count: qty })})` : part))
        .join(', '),
    ])
  if (profile.shop) rows.push([t('profile.shop'), profile.shop])

  const details = (
    <dl className="space-y-2">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt className="text-[length:var(--text-sm)] text-muted-foreground">{label}</dt>
          <dd className="text-[length:var(--text-body)]">{value}</dd>
        </div>
      ))}
    </dl>
  )

  if (profile.onboarding_done)
    return (
      <details className="group mx-4 mb-4 rounded-sm border border-ok bg-card px-4">
        <summary className="flex min-h-(--touch) cursor-pointer list-none items-center [&::-webkit-details-marker]:hidden gap-2 font-semibold text-ok">
          <Check aria-hidden className="size-5" />
          <span role="status">{t('profile.ready')}</span>
          <ChevronDown aria-hidden className="ml-auto size-5 text-muted-foreground group-open:rotate-180" />
        </summary>
        <div className="pb-4">{details}</div>
      </details>
    )

  return (
    <section aria-labelledby="profile-title" className="mx-4 mb-4 rounded-sm border border-border bg-card px-4 py-4">
      <h2 id="profile-title" className="font-heading text-[length:var(--text-lg)] font-bold">
        {t('profile.title')}
      </h2>
      <div className="mt-3">{details}</div>
    </section>
  )
}
