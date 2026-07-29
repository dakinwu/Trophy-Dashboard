import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { PlatformLogos } from '../components/PlatformLogos'
import { Spinner } from '../components/Spinner'
import type { PsnprofilesTrophy, Trophy, TrophyGrade } from '../lib/api'
import { useGameDetail, usePsnprofilesTrophies } from '../lib/queries'
import { GRADE_COLOR_VAR, parseRarityPercent, parseTrophyTimestamp } from '../lib/trophy'

type SortMode = 'earned' | 'order' | 'rarity' | 'grade'

interface EnrichedTrophy extends Trophy {
  psnprofiles_trophy_url?: string
}

const GRADE_PRIORITY: Record<TrophyGrade, number> = {
  Platinum: 0,
  Gold: 1,
  Silver: 2,
  Bronze: 3,
}

function normaliseTrophyTitle(title: string): string {
  return title
    .normalize('NFKC')
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

function mergePsnprofilesRarity(
  trophies: Trophy[],
  psnprofilesTrophies: PsnprofilesTrophy[],
): EnrichedTrophy[] {
  const byId = new Map(
    psnprofilesTrophies
      .filter((trophy) => trophy.trophy_id != null)
      .map((trophy) => [trophy.trophy_id, trophy]),
  )
  const byTitle = new Map(
    psnprofilesTrophies.map((trophy) => [normaliseTrophyTitle(trophy.title), trophy]),
  )
  return trophies.map((trophy) => {
    const match =
      (trophy.trophy_id != null ? byId.get(trophy.trophy_id) : undefined)
      ?? byTitle.get(normaliseTrophyTitle(trophy.title))
    if (!match) return trophy
    return {
      ...trophy,
      rarity_label: trophy.rarity_label ?? match.rarity_label,
      psnprofiles_rarity_percent: match.psnprofiles_rarity_percent,
      psnprofiles_trophy_url: match.trophy_url,
    }
  })
}

function earnedTimestamp(trophy: Trophy): number {
  return parseTrophyTimestamp(trophy.timestamp)?.getTime() ?? -1
}

function rarityLabel(trophy: Trophy): string {
  if (trophy.rarity_label) return trophy.rarity_label
  const percent = parseRarityPercent(
    trophy.psn_rarity_percent ?? trophy.psnprofiles_rarity_percent ?? trophy.rarity_percent,
  )
  if (!Number.isFinite(percent)) return 'Unknown rarity'
  if (percent <= 5) return 'Ultra Rare'
  if (percent <= 10) return 'Very Rare'
  if (percent <= 20) return 'Rare'
  if (percent <= 50) return 'Uncommon'
  return 'Common'
}

function formatEarnedTime(trophy: Trophy): string {
  if (trophy.earned === false) return 'Not earned'
  const date = parseTrophyTimestamp(trophy.timestamp)
  if (!date) return trophy.timestamp || 'Earned'
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function GameDetailPage() {
  const { username } = useParams<{ username: string }>()
  const [searchParams] = useSearchParams()
  const game = searchParams.get('game')?.trim() || undefined
  const detailQuery = useGameDetail(username, game)
  const [sortMode, setSortMode] = useState<SortMode>('earned')
  const detail = detailQuery.data
  const platform = detail?.platforms.find((value) => value !== 'UNKNOWN')
  const psnprofilesQuery = usePsnprofilesTrophies(detail?.display_name, platform)

  const trophies = useMemo(() => {
    if (!detail) return []
    const merged = mergePsnprofilesRarity(
      detail.trophies,
      psnprofilesQuery.data?.trophies ?? [],
    )
    return [...merged].sort((left, right) => {
      if (sortMode === 'order') {
        return (left.trophy_id ?? Number.MAX_SAFE_INTEGER)
          - (right.trophy_id ?? Number.MAX_SAFE_INTEGER)
      }
      if (sortMode === 'rarity') {
        return parseRarityPercent(left.psn_rarity_percent ?? left.rarity_percent)
          - parseRarityPercent(right.psn_rarity_percent ?? right.rarity_percent)
      }
      if (sortMode === 'grade') {
        return GRADE_PRIORITY[left.grade] - GRADE_PRIORITY[right.grade]
      }
      return earnedTimestamp(right) - earnedTimestamp(left)
    })
  }, [detail, psnprofilesQuery.data, sortMode])

  if (!game) {
    return <ErrorState title="No game selected" message="Return to Games and choose a title." />
  }

  if (detailQuery.isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (detailQuery.isError || !detail) {
    return (
      <ErrorState
        title="Game trophies unavailable"
        message={detailQuery.error?.message ?? 'This trophy list could not be loaded.'}
      />
    )
  }

  const earnedCount = detail.trophies.filter((trophy) => trophy.earned !== false).length
  const psnprofilesMatched = trophies.filter(
    (trophy) => trophy.psnprofiles_rarity_percent,
  ).length

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <Link
          to={`/u/${encodeURIComponent(username ?? '')}/games`}
          className="self-start text-sm text-muted transition hover:text-accent"
        >
          ← Back to Games
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-text">{detail.display_name}</h1>
            <p className="mt-1 text-sm text-muted">
              {earnedCount} of {detail.trophies.length} trophies earned
            </p>
          </div>
          <PlatformLogos platforms={detail.platforms} />
        </div>

        {!detail.complete && (
          <p className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm text-muted">
            This data source currently exposes earned trophies only; locked trophies are unavailable.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <div className="text-xs text-muted">
            {psnprofilesQuery.isFetching && 'Loading PSNProfiles tracked-player rarity…'}
            {!psnprofilesQuery.isFetching && psnprofilesQuery.data && (
              <>
                PSNProfiles matched {psnprofilesMatched} of {detail.trophies.length} trophies
                {' · '}
                <a
                  href={psnprofilesQuery.data.game_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:text-accent-bright"
                >
                  Open trophy list
                </a>
              </>
            )}
            {!psnprofilesQuery.isFetching && !psnprofilesQuery.data && (
              <span>
                PSNProfiles rarity is temporarily unavailable; official PSN data is still shown.
              </span>
            )}
          </div>
          <label className="flex items-center gap-2 text-xs text-muted">
            Sort
            <select
              value={sortMode}
              onChange={(event) => setSortMode(event.target.value as SortMode)}
              className="rounded-lg border border-border bg-bg px-2 py-1.5 text-sm text-text focus:border-accent focus:outline-none"
            >
              <option value="earned">Earned time</option>
              <option value="order">Trophy order</option>
              <option value="rarity">Official rarity</option>
              <option value="grade">Grade</option>
            </select>
          </label>
        </div>
      </section>

      <section className="flex flex-col gap-3" aria-label="Trophies">
        {trophies.map((trophy, index) => (
          <article
            key={`${trophy.trophy_id ?? index}-${trophy.title}`}
            className={[
              'grid gap-4 rounded-xl border border-border bg-surface p-4 sm:grid-cols-[72px_minmax(0,1fr)_minmax(250px,auto)] sm:items-center',
              trophy.earned === false ? 'opacity-65' : '',
            ].join(' ')}
          >
            <img
              src={trophy.icon_url}
              alt=""
              loading="lazy"
              className="h-16 w-16 rounded-lg border border-border object-cover"
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-text">{trophy.title}</h2>
                <span
                  className="rounded-full border px-2 py-0.5 text-[11px] font-medium"
                  style={{
                    color: GRADE_COLOR_VAR[trophy.grade],
                    borderColor: GRADE_COLOR_VAR[trophy.grade],
                  }}
                >
                  {trophy.grade}
                </span>
              </div>
              {trophy.description && (
                <p className="mt-1 text-sm text-muted">{trophy.description}</p>
              )}
              <p
                className={`mt-2 text-xs ${
                  trophy.earned === false ? 'text-muted' : 'text-accent'
                }`}
              >
                {formatEarnedTime(trophy)}
              </p>
            </div>

            <dl className="grid grid-cols-2 gap-x-5 gap-y-2 text-xs sm:min-w-[250px]">
              <div>
                <dt className="text-muted">Rarity</dt>
                <dd className="mt-0.5 font-medium text-text">{rarityLabel(trophy)}</dd>
              </div>
              <div>
                <dt className="text-muted">PSN official</dt>
                <dd className="mt-0.5 font-medium text-text">
                  {trophy.psn_rarity_percent ?? 'N/A'}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">PSNProfiles tracked players</dt>
                <dd className="mt-0.5 font-medium text-text">
                  {trophy.psnprofiles_trophy_url ? (
                    <a
                      href={trophy.psnprofiles_trophy_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent hover:text-accent-bright"
                    >
                      {trophy.psnprofiles_rarity_percent ?? 'N/A'}
                    </a>
                  ) : (
                    trophy.psnprofiles_rarity_percent ?? 'N/A'
                  )}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </section>
    </div>
  )
}
