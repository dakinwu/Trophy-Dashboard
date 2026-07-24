import type { TrophyGrade } from '../lib/api'
import type { GameSummary } from '../lib/games'
import { GRADE_COLOR_VAR } from '../lib/trophy'

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

      {/* Real completion %, playtime, difficulty, and external links land in Phase 3. */}
      <div className="rounded-lg border border-dashed border-border bg-bg/30 px-2 py-1.5 text-center text-[11px] text-muted opacity-70">
        Completion %, playtime & links — more coming
      </div>
    </div>
  )
}
