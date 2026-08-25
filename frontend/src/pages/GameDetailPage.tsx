import { ListBox, Select } from '@heroui/react'
import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { PlatformLogos } from '../components/PlatformLogos'
import { Spinner } from '../components/Spinner'
import type { PsnprofilesTrophy, Trophy, TrophyGrade } from '../lib/api'
import { useGameDetail, usePsnprofilesTrophies } from '../lib/queries'
import { GRADE_COLOR_VAR, GRADE_LABEL, parseRarityPercent, parseTrophyTimestamp } from '../lib/trophy'

type SortMode = 'order' | 'officialRarity' | 'psnprofilesRarity' | 'earned' | 'grade'
type EarnedFilter = 'all' | 'earned' | 'locked'

interface EnrichedTrophy extends Trophy {
  psnprofiles_trophy_url?: string
}

const GRADE_PRIORITY: Record<TrophyGrade, number> = {
  Platinum: 0,
  Gold: 1,
  Silver: 2,
  Bronze: 3,
}

const GRADE_SYMBOL: Record<TrophyGrade, string> = {
  Platinum: '✦',
  Gold: '★',
  Silver: '◆',
  Bronze: '●',
}

const SORT_OPTIONS: Array<{ id: SortMode; label: string }> = [
  { id: 'order', label: '預設獎盃順序' },
  { id: 'officialRarity', label: 'PSN 官方稀有度' },
  { id: 'psnprofilesRarity', label: 'PSNProfiles 稀有度' },
  { id: 'earned', label: '取得時間' },
  { id: 'grade', label: '獎盃類型' },
]

const EARNED_FILTER_OPTIONS: Array<{ id: EarnedFilter; label: string }> = [
  { id: 'all', label: '所有獎盃' },
  { id: 'earned', label: '已取得' },
  { id: 'locked', label: '尚未取得' },
]

function normaliseTrophyTitle(title: string): string {
  return title
    .normalize('NFKC')
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

function selectPsnprofilesRarity(
  trophy: Trophy,
  match: PsnprofilesTrophy,
): string | null {
  const official = trophy.psn_rarity_percent
    ? parseRarityPercent(trophy.psn_rarity_percent)
    : Number.POSITIVE_INFINITY
  const candidates = match.rarity_percentages ?? []
  if (Number.isFinite(official)) {
    const tracked = candidates.find(
      (candidate) => Math.abs(parseRarityPercent(candidate) - official) > 0.0001,
    )
    if (tracked) return tracked
  }
  return match.psnprofiles_rarity_percent
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
      byTitle.get(normaliseTrophyTitle(trophy.title))
      ?? (trophy.trophy_id != null ? byId.get(trophy.trophy_id) : undefined)
    if (!match) return trophy
    return {
      ...trophy,
      rarity_label: trophy.rarity_label ?? match.rarity_label,
      psnprofiles_rarity_percent: selectPsnprofilesRarity(trophy, match),
      psnprofiles_trophy_url: match.trophy_url,
    }
  })
}

function earnedTimestamp(trophy: Trophy): number {
  return parseTrophyTimestamp(trophy.timestamp)?.getTime() ?? -1
}

function rarityLabel(trophy: Trophy): string {
  const translated = {
    'Ultra Rare': '極度稀有',
    'Very Rare': '非常稀有',
    Rare: '稀有',
    Uncommon: '不常見',
    Common: '常見',
  } as const
  if (trophy.rarity_label) {
    return translated[trophy.rarity_label as keyof typeof translated] ?? trophy.rarity_label
  }
  const percent = parseRarityPercent(
    trophy.psn_rarity_percent ?? trophy.psnprofiles_rarity_percent ?? trophy.rarity_percent,
  )
  if (!Number.isFinite(percent)) return '稀有度未知'
  if (percent <= 5) return '極度稀有'
  if (percent <= 10) return '非常稀有'
  if (percent <= 20) return '稀有'
  if (percent <= 50) return '不常見'
  return '常見'
}

function formatEarnedTime(trophy: Trophy): string {
  if (trophy.earned === false) return '尚未取得'
  const date = parseTrophyTimestamp(trophy.timestamp)
  if (!date) return trophy.timestamp || '已取得'
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
  const [sortMode, setSortMode] = useState<SortMode>('order')
  const [earnedFilter, setEarnedFilter] = useState<EarnedFilter>('all')
  const detail = detailQuery.data
  const platform = detail?.platforms.find((value) => value !== 'UNKNOWN')
  const psnprofilesQuery = usePsnprofilesTrophies(detail?.display_name, platform)

  const enrichedTrophies = useMemo(() => {
    if (!detail) return []
    return mergePsnprofilesRarity(
      detail.trophies,
      psnprofilesQuery.data?.trophies ?? [],
    )
  }, [detail, psnprofilesQuery.data])

  const trophies = useMemo(() => {
    const filtered = enrichedTrophies.filter((trophy) => {
      if (earnedFilter === 'earned') return trophy.earned !== false
      if (earnedFilter === 'locked') return trophy.earned === false
      return true
    })
    const trophyOrder = (trophy: Trophy) => trophy.trophy_id ?? Number.MAX_SAFE_INTEGER

    return [...filtered].sort((left, right) => {
      let priority = 0
      if (sortMode === 'officialRarity') {
        priority = parseRarityPercent(left.psn_rarity_percent ?? left.rarity_percent)
          - parseRarityPercent(right.psn_rarity_percent ?? right.rarity_percent)
      } else if (sortMode === 'psnprofilesRarity') {
        priority = parseRarityPercent(left.psnprofiles_rarity_percent ?? '')
          - parseRarityPercent(right.psnprofiles_rarity_percent ?? '')
      } else if (sortMode === 'grade') {
        priority = GRADE_PRIORITY[left.grade] - GRADE_PRIORITY[right.grade]
      } else if (sortMode === 'earned') {
        priority = earnedTimestamp(right) - earnedTimestamp(left)
      }
      return priority || trophyOrder(left) - trophyOrder(right)
    })
  }, [earnedFilter, enrichedTrophies, sortMode])

  if (!game) {
    return <ErrorState title="尚未選擇遊戲" message="請返回遊戲頁面並選擇一款遊戲。" />
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
        title="無法取得遊戲獎盃"
        message="目前無法載入這份獎盃列表。"
      />
    )
  }

  const earnedCount = detail.trophies.filter((trophy) => trophy.earned !== false).length
  const psnprofilesMatched = enrichedTrophies.filter(
    (trophy) => trophy.psnprofiles_rarity_percent,
  ).length

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 sm:p-6">
        <Link
          to={`/u/${encodeURIComponent(username ?? '')}/games`}
          className="self-start text-sm text-muted transition hover:text-accent"
        >
          ← 返回遊戲
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-text">{detail.display_name}</h1>
            <p className="mt-1 text-sm text-muted">
              已取得 {earnedCount}／{detail.trophies.length} 座獎盃
            </p>
          </div>
          <PlatformLogos platforms={detail.platforms} />
        </div>

        {!detail.complete && (
          <p className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm text-muted">
            目前的資料來源只提供已取得的獎盃，無法顯示尚未取得的獎盃。
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <div className="text-xs text-muted">
            {psnprofilesQuery.isFetching && '正在載入 PSNProfiles 追蹤玩家稀有度…'}
            {!psnprofilesQuery.isFetching && psnprofilesQuery.data && (
              <>
                PSNProfiles 已媒合 {psnprofilesMatched}／{detail.trophies.length} 座獎盃
                {' · '}
                <a
                  href={psnprofilesQuery.data.game_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:text-accent-bright"
                >
                  開啟獎盃列表
                </a>
              </>
            )}
            {!psnprofilesQuery.isFetching && !psnprofilesQuery.data && (
              <span>
                PSNProfiles 稀有度暫時無法取得，目前仍顯示 PSN 官方資料。
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
            <div className="flex items-center gap-2">
              <span id="trophy-sort-label">排序方式</span>
              <Select
                aria-labelledby="trophy-sort-label"
                selectedKey={sortMode}
                onSelectionChange={(key) => setSortMode(key as SortMode)}
                variant="secondary"
                className="min-w-44"
              >
                <Select.Trigger>
                  <Select.Value />
                  <Select.Indicator />
                </Select.Trigger>
                <Select.Popover>
                  <ListBox>
                    {SORT_OPTIONS.map((option) => (
                      <ListBox.Item key={option.id} id={option.id} textValue={option.label}>
                        {option.label}
                        <ListBox.ItemIndicator />
                      </ListBox.Item>
                    ))}
                  </ListBox>
                </Select.Popover>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span id="trophy-earned-filter-label">取得狀態</span>
              <Select
                aria-labelledby="trophy-earned-filter-label"
                selectedKey={earnedFilter}
                onSelectionChange={(key) => setEarnedFilter(key as EarnedFilter)}
                variant="secondary"
                className="min-w-36"
              >
                <Select.Trigger>
                  <Select.Value />
                  <Select.Indicator />
                </Select.Trigger>
                <Select.Popover>
                  <ListBox>
                    {EARNED_FILTER_OPTIONS.map((option) => (
                      <ListBox.Item key={option.id} id={option.id} textValue={option.label}>
                        {option.label}
                        <ListBox.ItemIndicator />
                      </ListBox.Item>
                    ))}
                  </ListBox>
                </Select.Popover>
              </Select>
            </div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3" aria-label="獎盃">
        {trophies.length === 0 && (
          <p className="rounded-xl border border-border bg-surface p-5 text-sm text-muted">
            沒有符合目前狀態篩選的獎盃。
          </p>
        )}
        {trophies.map((trophy, index) => (
          <article
            key={`${trophy.trophy_id ?? index}-${trophy.title}`}
            className={[
              'grid gap-4 rounded-xl border border-border bg-surface p-4 sm:grid-cols-[72px_minmax(0,1fr)_minmax(250px,auto)] sm:items-center',
            ].join(' ')}
          >
            <img
              src={trophy.icon_url}
              alt=""
              loading="lazy"
              className="h-16 w-16 rounded-lg border-2 object-cover"
              style={{ borderColor: GRADE_COLOR_VAR[trophy.grade] }}
            />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-text">{trophy.title}</h2>
                <span
                  aria-label={`${GRADE_LABEL[trophy.grade]}獎盃`}
                  className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-bold tracking-wide"
                  style={{
                    color: GRADE_COLOR_VAR[trophy.grade],
                    borderColor: GRADE_COLOR_VAR[trophy.grade],
                    backgroundColor: `color-mix(in srgb, ${GRADE_COLOR_VAR[trophy.grade]} 16%, transparent)`,
                  }}
                >
                  <span aria-hidden="true" className="text-sm leading-none">
                    {GRADE_SYMBOL[trophy.grade]}
                  </span>
                  {GRADE_LABEL[trophy.grade]}
                </span>
                {trophy.is_dlc && (
                  <span className="rounded-full border border-accent/60 px-2 py-0.5 text-[11px] font-medium text-accent">
                    DLC
                  </span>
                )}
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
                <dt className="text-muted">稀有度</dt>
                <dd className="mt-0.5 font-medium text-text">{rarityLabel(trophy)}</dd>
              </div>
              <div>
                <dt className="text-muted">PSN 官方</dt>
                <dd className="mt-0.5 font-medium text-text">
                  {trophy.psn_rarity_percent ?? '無法取得'}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">PSNProfiles 追蹤玩家</dt>
                <dd className="mt-0.5 font-medium text-text">
                  {trophy.psnprofiles_trophy_url ? (
                    <a
                      href={trophy.psnprofiles_trophy_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent hover:text-accent-bright"
                    >
                      {trophy.psnprofiles_rarity_percent ?? '無法取得'}
                    </a>
                  ) : (
                    trophy.psnprofiles_rarity_percent ?? '無法取得'
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
