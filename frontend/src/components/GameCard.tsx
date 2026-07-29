import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { TrophyGrade } from '../lib/api'
import type { GameSummary } from '../lib/games'
import { formatPlaytime } from '../lib/games'
import { GRADE_COLOR_VAR } from '../lib/trophy'
import { useHltb, usePsnprofilesGuide } from '../lib/queries'
import { ExternalLinks } from './ExternalLinks'
import { PlatformLogos } from './PlatformLogos'

const GRADE_ORDER: TrophyGrade[] = ['Platinum', 'Gold', 'Silver', 'Bronze']

export function GameCard({ summary, username }: { summary: GameSummary; username: string }) {
  const [guideRequested, setGuideRequested] = useState(false)
  const hltb = useHltb(summary.displayName)
  const psnprofilesGuide = usePsnprofilesGuide(summary.displayName, guideRequested)
  const guide = psnprofilesGuide.data

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-md shadow-black/10 transition hover:-translate-y-0.5 hover:shadow-lg">
      <Link
        to={`/u/${encodeURIComponent(username)}/games/detail?game=${encodeURIComponent(summary.game)}`}
        className="flex items-center gap-3 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        aria-label={`View ${summary.displayName} trophies`}
      >
        <img
          src={summary.iconUrl}
          alt=""
          loading="lazy"
          className="h-14 w-14 shrink-0 rounded-lg border border-border object-cover"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <h3
              className="min-w-0 flex-1 truncate text-sm font-semibold text-text"
              title={summary.displayName}
            >
              {summary.displayName}
            </h3>
            <PlatformLogos platforms={summary.platforms} />
          </div>
          <p className="text-xs text-muted">
            {summary.totalEarned} trophies
            {summary.hasPlatinum && <span className="ml-1 text-platinum">· Platinum</span>}
          </p>
        </div>
      </Link>

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

      {hltb.data && hltb.data.main_story > 0 && (
        <p className="text-xs text-muted">
          HLTB: <span className="text-text">{Math.round(hltb.data.main_story)}h</span> main
          {hltb.data.completionist > 0 && (
            <>
              {' · '}
              <span className="text-text">{Math.round(hltb.data.completionist)}h</span> 100%
            </>
          )}
        </p>
      )}

      {guide && (guide.difficulty || guide.platinum_time) && (
        <p className="text-xs text-muted">
          PSNProfiles:
          {guide.difficulty && <span className="ml-1 text-text">{guide.difficulty}</span>}
          {guide.difficulty && guide.platinum_time && <span> · </span>}
          {guide.platinum_time && <span className="text-text">{guide.platinum_time}</span>}
        </p>
      )}

      {!guideRequested && (
        <button
          type="button"
          onClick={() => setGuideRequested(true)}
          className="self-start text-xs font-medium text-muted underline decoration-border underline-offset-2 transition hover:text-accent"
        >
          Load PSNProfiles guide details
        </button>
      )}
      {guideRequested && psnprofilesGuide.isFetching && (
        <p className="text-xs text-muted">Loading PSNProfiles guide…</p>
      )}
      {guideRequested && !psnprofilesGuide.isFetching && psnprofilesGuide.isSuccess && !guide && (
        <button
          type="button"
          onClick={() => void psnprofilesGuide.refetch()}
          className="self-start text-xs font-medium text-muted underline decoration-border underline-offset-2 transition hover:text-accent"
        >
          Guide unavailable · retry
        </button>
      )}

      <Link
        to={`/u/${encodeURIComponent(username)}/games/detail?game=${encodeURIComponent(summary.game)}`}
        className="self-start text-xs font-semibold text-accent transition hover:text-accent-bright"
      >
        View trophies →
      </Link>

      <div className="flex flex-col gap-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wide text-muted">Guides &amp; info</span>
        <ExternalLinks game={summary.displayName} psnprofilesGuideUrl={guide?.guide_url} />
      </div>
    </div>
  )
}
