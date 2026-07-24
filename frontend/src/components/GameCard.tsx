import type { TrophyGrade } from '../lib/api'
import type { GameSummary } from '../lib/games'
import { formatPlaytime } from '../lib/games'
import { GRADE_COLOR_VAR } from '../lib/trophy'
import { ExternalLinks } from './ExternalLinks'

const GRADE_ORDER: TrophyGrade[] = ['Platinum', 'Gold', 'Silver', 'Bronze']

export function GameCard({ summary }: { summary: GameSummary }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-md shadow-black/10 transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="flex items-center gap-3">
        <img
          src={summary.iconUrl}
          alt=""
          loading="lazy"
          className="h-14 w-14 shrink-0 rounded-lg border border-border object-cover"
        />
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-text" title={summary.game}>
            {summary.game}
          </h3>
          <p className="text-xs text-muted">
            {summary.totalEarned} trophies
            {summary.hasPlatinum && <span className="ml-1 text-platinum">· Platinum</span>}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs">
        {GRADE_ORDER.map((grade) => (
          <span
            key={grade}
            className="rounded-full border px-2 py-0.5 font-medium"
            style={{ color: GRADE_COLOR_VAR[grade], borderColor: GRADE_COLOR_VAR[grade] }}
          >
            {summary.counts[grade]}
          </span>
        ))}
      </div>

      <p className="text-xs text-muted">
        Last earned:{' '}
        {summary.lastEarnedDate
          ? summary.lastEarnedDate.toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })
          : 'Unknown'}
      </p>

      {summary.playtimeSeconds != null && (
        <p className="text-xs text-muted">
          Playtime: <span className="font-medium text-accent">{formatPlaytime(summary.playtimeSeconds)}</span>
        </p>
      )}

      {/* External guide/info links (Phase 3A). Completion % and difficulty land in Phase 3B. */}
      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wide text-muted">Guides &amp; info</span>
        <ExternalLinks game={summary.game} />
      </div>
    </div>
  )
}
