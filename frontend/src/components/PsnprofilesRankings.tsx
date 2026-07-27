import { useMemo, useState } from 'react'
import type { ProfileSummary, PsnprofilesStats } from '../lib/api'
import { usePsnprofilesStats } from '../lib/queries'

function rankFromStats(summary: ProfileSummary): PsnprofilesStats | null {
  const world = Number.parseInt((summary.stats['World Rank'] ?? '').replaceAll(',', ''), 10)
  const countryEntry = Object.entries(summary.stats).find(
    ([label]) => !['World Rank', 'Level Rank'].includes(label) && label.endsWith(' Rank'),
  )
  const country = Number.parseInt((countryEntry?.[1] ?? '').replaceAll(',', ''), 10)
  if (!Number.isFinite(world) && !Number.isFinite(country)) return null

  return {
    world_rank: Number.isFinite(world) ? world : null,
    country_rank: Number.isFinite(country) ? country : null,
    country_label: countryEntry?.[0] ?? 'Country Rank',
    completion: summary.stats.Completion ?? null,
    profile_url: `https://psnprofiles.com/${encodeURIComponent(summary.username)}`,
  }
}

function formatRank(rank: number | null): string {
  return rank == null ? 'Unavailable' : `#${rank.toLocaleString()}`
}

export function PsnprofilesRankings({ summary }: { summary: ProfileSummary }) {
  const embedded = useMemo(() => rankFromStats(summary), [summary])
  const [requested, setRequested] = useState(false)
  const query = usePsnprofilesStats(summary.username, requested && !embedded)
  const rankings = embedded ?? query.data

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">PSNProfiles Rankings</h2>
          <p className="mt-1 text-xs text-muted">
            Ranking among public profiles tracked by PSNProfiles, not an official Sony leaderboard.
          </p>
        </div>

        {!rankings && !requested && (
          <button
            type="button"
            onClick={() => setRequested(true)}
            className="rounded-lg border border-border bg-bg/40 px-3 py-1.5 text-xs font-medium text-muted transition hover:border-accent hover:text-accent"
          >
            Load rankings
          </button>
        )}
      </div>

      {requested && query.isFetching && (
        <p className="mt-4 text-sm text-muted">Opening PSNProfiles and loading rankings…</p>
      )}

      {rankings && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <a
            href={rankings.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-border bg-bg/40 p-4 transition hover:border-accent"
          >
            <div className="text-2xl font-bold text-accent">{formatRank(rankings.world_rank)}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">World Rank</div>
          </a>
          <a
            href={rankings.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-border bg-bg/40 p-4 transition hover:border-accent"
          >
            <div className="text-2xl font-bold text-accent">{formatRank(rankings.country_rank)}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">
              {rankings.country_label ?? 'Country Rank'}
            </div>
          </a>
        </div>
      )}

      {requested && !query.isFetching && query.isSuccess && !rankings && (
        <div className="mt-4 flex items-center gap-3">
          <p className="text-sm text-muted">
            Rankings unavailable. The profile must be public and have a country on PSNProfiles.
          </p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className="text-xs font-medium text-accent underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      )}
    </section>
  )
}
