import { Button } from '@heroui/react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { TrophyGrade } from '../lib/api'
import type { GameSummary } from '../lib/games'
import { formatPlaytime } from '../lib/games'
import { GRADE_COLOR_VAR } from '../lib/trophy'
import { useHltb, usePsnprofilesGuide } from '../lib/queries'
import { ExternalLinks } from './ExternalLinks'
import { MagicCard } from './magicui/MagicCard'
import { PlatformLogos } from './PlatformLogos'

const GRADE_ORDER: TrophyGrade[] = ['Platinum', 'Gold', 'Silver', 'Bronze']
const GRADE_SHORT_LABEL: Record<TrophyGrade, string> = {
  Platinum: 'P',
  Gold: 'G',
  Silver: 'S',
  Bronze: 'B',
}

export function GameCard({ summary, username }: { summary: GameSummary; username: string }) {
  const [guideRequested, setGuideRequested] = useState(false)
  const hltb = useHltb(summary.displayName)
  const psnprofilesGuide = usePsnprofilesGuide(summary.displayName, guideRequested)
  const guide = psnprofilesGuide.data
  const detailUrl = `/u/${encodeURIComponent(username)}/games/detail?game=${encodeURIComponent(summary.game)}`
  const lastEarned = summary.lastEarnedDate
    ? summary.lastEarnedDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Unknown'

  return (
    <MagicCard className="h-full rounded-2xl transition duration-300 hover:-translate-y-1 hover:shadow-[0_18px_45px_rgba(0,0,0,0.32)]">
      <article className="flex h-full min-h-[26rem] flex-col">
        <Link
          to={detailUrl}
          className="group/header relative overflow-hidden border-b border-border/70 p-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
          aria-label={`View ${summary.displayName} trophies`}
        >
          <div
            aria-hidden="true"
            className="absolute inset-0 scale-125 bg-cover bg-center opacity-20 blur-2xl transition duration-500 group-hover/header:scale-150 group-hover/header:opacity-30"
            style={{ backgroundImage: `url(${JSON.stringify(summary.iconUrl).slice(1, -1)})` }}
          />
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-gradient-to-br from-surface/55 via-surface/90 to-bg"
          />

          <div className="relative flex items-start gap-3">
            <img
              src={summary.iconUrl}
              alt=""
              loading="lazy"
              className="h-[4.5rem] w-[4.5rem] shrink-0 rounded-xl border border-white/15 object-cover shadow-xl shadow-black/30 ring-1 ring-accent/15 transition duration-300 group-hover/header:scale-[1.04] group-hover/header:ring-accent/40"
            />
            <div className="min-w-0 flex-1 pt-0.5">
              <h3
                className="line-clamp-2 min-h-10 text-sm font-bold leading-5 text-text transition group-hover/header:text-accent-bright"
                title={summary.displayName}
              >
                {summary.displayName}
              </h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <PlatformLogos platforms={summary.platforms} />
                {summary.hasPlatinum && (
                  <span className="rounded-md border border-platinum/60 bg-platinum/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-platinum shadow-[0_0_18px_rgba(90,182,240,0.12)]">
                    ✦ Platinum
                  </span>
                )}
              </div>
            </div>
          </div>
        </Link>

        <div className="flex flex-1 flex-col p-4">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                Earned trophies
              </p>
              <p className="mt-0.5 text-2xl font-bold tabular-nums text-text">
                {summary.totalEarned.toLocaleString()}
              </p>
            </div>
            <span className="mb-1 text-[10px] text-muted">Trophy mix</span>
          </div>

          <div
            className="mt-3 flex h-1.5 overflow-hidden rounded-full bg-bg"
            aria-label="Earned trophy grade distribution"
          >
            {GRADE_ORDER.map((grade) =>
              summary.counts[grade] > 0 ? (
                <span
                  key={grade}
                  title={`${grade}: ${summary.counts[grade]}`}
                  className="h-full min-w-1"
                  style={{
                    backgroundColor: GRADE_COLOR_VAR[grade],
                    flexGrow: summary.counts[grade],
                  }}
                />
              ) : null,
            )}
          </div>

          <div className="mt-3 grid grid-cols-4 gap-1.5">
            {GRADE_ORDER.map((grade) => (
              <div
                key={grade}
                className="flex items-center justify-center gap-1 rounded-lg border px-1.5 py-1.5 text-xs font-bold tabular-nums"
                title={`${grade}: ${summary.counts[grade]}`}
                style={{
                  color: GRADE_COLOR_VAR[grade],
                  borderColor: `color-mix(in srgb, ${GRADE_COLOR_VAR[grade]} 42%, transparent)`,
                  backgroundColor: `color-mix(in srgb, ${GRADE_COLOR_VAR[grade]} 8%, transparent)`,
                }}
              >
                <span className="text-[9px] font-black opacity-75">{GRADE_SHORT_LABEL[grade]}</span>
                {summary.counts[grade]}
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-border/70 bg-bg/35 p-2.5">
              <p className="text-[10px] uppercase tracking-wide text-muted">Last earned</p>
              <p className="mt-1 truncate text-xs font-semibold text-text" title={lastEarned}>
                {lastEarned}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-bg/35 p-2.5">
              <p className="text-[10px] uppercase tracking-wide text-muted">Playtime</p>
              <p className="mt-1 text-xs font-semibold text-accent">
                {summary.playtimeSeconds != null
                  ? formatPlaytime(summary.playtimeSeconds)
                  : 'Unavailable'}
              </p>
            </div>
          </div>

          {hltb.data && hltb.data.main_story > 0 && (
            <div className="mt-2 rounded-lg border border-border/70 bg-bg/35 px-3 py-2 text-xs text-muted">
              <span className="font-semibold text-text">HLTB</span>
              <span className="mx-1.5 text-border">·</span>
              <span className="text-text">{Math.round(hltb.data.main_story)}h</span> main
              {hltb.data.completionist > 0 && (
                <>
                  <span className="mx-1.5 text-border">·</span>
                  <span className="text-text">{Math.round(hltb.data.completionist)}h</span> 100%
                </>
              )}
            </div>
          )}

          {guide && (guide.difficulty || guide.platinum_time) && (
            <div className="mt-2 rounded-lg border border-accent/25 bg-accent/5 px-3 py-2 text-xs text-muted">
              <span className="font-semibold text-accent">PSNProfiles</span>
              {guide.difficulty && <span className="ml-1.5 text-text">{guide.difficulty}</span>}
              {guide.difficulty && guide.platinum_time && <span className="text-border"> · </span>}
              {guide.platinum_time && <span className="text-text">{guide.platinum_time}</span>}
            </div>
          )}

          <div className="mt-auto pt-4">
            <Link
              to={detailUrl}
              className="group flex w-full items-center justify-between rounded-lg border border-accent/35 bg-accent/10 px-3 py-2 text-xs font-bold text-accent transition hover:border-accent hover:bg-accent/15 hover:text-accent-bright focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <span>View trophy list</span>
              <span aria-hidden="true" className="transition group-hover:translate-x-0.5">
                →
              </span>
            </Link>

            {!guideRequested && (
              <Button
                type="button"
                onPress={() => setGuideRequested(true)}
                size="sm"
                variant="ghost"
                className="mt-1.5 w-full text-xs text-muted"
              >
                Load PSNProfiles guide details
              </Button>
            )}
            {guideRequested && psnprofilesGuide.isFetching && (
              <p className="mt-2 text-center text-xs text-muted">Loading PSNProfiles guide…</p>
            )}
            {guideRequested &&
              !psnprofilesGuide.isFetching &&
              psnprofilesGuide.isSuccess &&
              !guide && (
                <Button
                  type="button"
                  onPress={() => void psnprofilesGuide.refetch()}
                  size="sm"
                  variant="ghost"
                  className="mt-1.5 w-full text-xs text-muted"
                >
                  Guide unavailable · retry
                </Button>
              )}

            <div className="mt-3 border-t border-border/60 pt-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                Guides &amp; info
              </p>
              <ExternalLinks game={summary.displayName} psnprofilesGuideUrl={guide?.guide_url} />
            </div>
          </div>
        </div>
      </article>
    </MagicCard>
  )
}
