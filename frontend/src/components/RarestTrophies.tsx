import { useState } from 'react'
import type { Trophy } from '../lib/api'
import { ImageWithFallback } from './ImageWithFallback'
import {
  GRADE_COLOR_VAR,
  getRarestTrophies,
  rarityForSource,
  type RarityRankingSource,
} from '../lib/trophy'
import { BorderBeam } from './magicui/BorderBeam'

export function RarestTrophies({ trophies }: { trophies: Trophy[] }) {
  const [source, setSource] = useState<RarityRankingSource>('psn')
  const rarest = getRarestTrophies(trophies, 5, source)
  const coverage = trophies.filter((trophy) => rarityForSource(trophy, source)).length

  return (
    <section className="relative overflow-hidden rounded-2xl border border-border bg-surface p-5">
      <BorderBeam size={110} duration={13} delay={7} reverse colorTo="var(--bronze)" />
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-text">最稀有獎盃</h2>
        <div className="flex rounded-lg border border-border bg-bg/50 p-1" aria-label="稀有度來源">
          {(['psn', 'psnprofiles'] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setSource(value)}
              aria-pressed={source === value}
              className={[
                'rounded-md px-3 py-1 text-xs font-semibold transition',
                source === value
                  ? 'bg-accent/20 text-accent-bright'
                  : 'text-muted hover:text-text',
              ].join(' ')}
            >
              {value === 'psn' ? 'PSN 官方' : 'PSNProfiles'}
            </button>
          ))}
        </div>
      </div>
      <p className="mb-3 text-xs text-muted">
        {source === 'psn'
          ? `PSN 官方稀有度涵蓋 ${coverage.toLocaleString()}／${trophies.length.toLocaleString()} 座已取得獎盃。`
          : `PSNProfiles 快取涵蓋 ${coverage.toLocaleString()}／${trophies.length.toLocaleString()} 座已取得獎盃；開啟個別遊戲的獎盃頁面即可補充追蹤玩家資料。`}
      </p>
      {rarest.length === 0 ? (
        <p className="text-sm text-muted">
          {source === 'psnprofiles'
            ? '目前還沒有可用的 PSNProfiles 稀有度快取。'
            : '目前沒有 PSN 官方獎盃稀有度資料。'}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rarest.map((trophy, index) => (
            <li
              key={`${trophy.game}-${trophy.title}-${index}`}
              className="flex items-center gap-3 rounded-lg border border-border bg-bg/40 p-2 transition hover:-translate-y-0.5 hover:bg-bg/70"
            >
              <ImageWithFallback
                src={trophy.icon_url}
                alt=""
                loading="lazy"
                className="h-10 w-10 shrink-0 rounded-md object-cover"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-text">{trophy.title}</p>
                <p className="truncate text-xs text-muted">{trophy.game}</p>
              </div>
              <span
                className="shrink-0 rounded-full border px-2 py-1 text-xs font-semibold"
                style={{
                  color: GRADE_COLOR_VAR[trophy.grade],
                  borderColor: GRADE_COLOR_VAR[trophy.grade],
                }}
              >
                {source === 'psn' ? 'PSN' : 'PSNP'} {rarityForSource(trophy, source)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
