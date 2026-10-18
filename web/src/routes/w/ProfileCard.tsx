import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { ProfileView } from '@/audio/profile'

// The onboarding profile card (T21, G1): fills in as each answer is saved; appliances show as chips.
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

  return (
    <section aria-labelledby="profile-title" className="mx-4 mb-4 rounded-sm border border-border bg-card px-4 py-4">
      <h2 id="profile-title" className="font-heading text-[length:var(--text-lg)] font-bold">
        {t('profile.title')}
      </h2>
      <dl className="mt-3 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[length:var(--text-sm)] text-muted-foreground">{label}</dt>
            <dd className="text-[length:var(--text-body)]">{value}</dd>
          </div>
        ))}
      </dl>
      {profile.onboarding_done && (
        <p role="status" className="mt-3 inline-flex items-center gap-1 font-semibold text-ok">
          <Check aria-hidden className="size-4" /> {t('profile.ready')}
        </p>
      )}
    </section>
  )
}
