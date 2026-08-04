import type { ProfileData, Trophy, TrophyCounts, TrophyGrade } from './api'
import { parseTrophyTimestamp, rarityForSource, type RarityRankingSource } from './trophy'

export type HeroMetricTone = 'accent' | 'platinum' | 'text' | 'muted'

export interface HeroMetric {
  key: string
  label: string
  value: number | string
  numeric: boolean
  tone: HeroMetricTone
  detail?: string
}

export interface TrophyMixItem {
  grade: TrophyGrade
  count: number
  percentage: number
}

export interface HeroRarityBucket {
  label: string
  count: number
  maxPercent: number
}

export interface RecentTrophyItem {
  trophy: Trophy
  earnedAt: Date
}

export interface OverviewHeroViewModel {
  username: string
  avatarUrl: string | null
  level: string | null
  levelProgress: number | null
  source: 'psn' | 'psnprofiles' | 'unknown'
  sourceLabel: string
  cacheStatus: 'live' | 'cached' | 'unknown'
  fetchedAt: Date | null
  metrics: HeroMetric[]
  trophyMix: TrophyMixItem[]
  raritySource: RarityRankingSource | null
  raritySourceLabel: 'PSN' | 'PSNP' | null
  rarityBuckets: HeroRarityBucket[]
  recentTrophies: RecentTrophyItem[]
  gamesPlayed: number | null
  completedGames: number | null
  completionPercent: number | null
  totalTrophies: number
}

const GRADE_ORDER: TrophyGrade[] = ['Platinum', 'Gold', 'Silver', 'Bronze']
const RARITY_BUCKETS = [
  { label: 'Ultra Rare', maxPercent: 5 },
  { label: 'Very Rare', maxPercent: 10 },
  { label: 'Rare', maxPercent: 20 },
  { label: 'Uncommon', maxPercent: 50 },
  { label: 'Common', maxPercent: Number.POSITIVE_INFINITY },
] as const

function parseNumber(value: string | undefined): number | null {
  if (!value) return null
  const parsed = Number.parseFloat(value.replaceAll(',', '').replace('%', '').trim())
  return Number.isFinite(parsed) ? parsed : null
}

function profileSource(data: ProfileData): OverviewHeroViewModel['source'] {
  if (data.profile_source) return data.profile_source
  const label = data.profile_summary.stats.Source?.toLowerCase() ?? ''
  if (label.includes('psn api')) return 'psn'
  if (label.includes('psnprofiles')) return 'psnprofiles'
  return 'unknown'
}

function primaryRaritySource(trophies: Trophy[]): RarityRankingSource | null {
  if (trophies.some((trophy) => rarityForSource(trophy, 'psn') !== null)) return 'psn'
  if (trophies.some((trophy) => rarityForSource(trophy, 'psnprofiles') !== null)) {
    return 'psnprofiles'
  }
  return null
}

function buildRarityBuckets(
  trophies: Trophy[],
  source: RarityRankingSource | null,
): HeroRarityBucket[] {
  const buckets = RARITY_BUCKETS.map((bucket) => ({ ...bucket, count: 0 }))
  if (!source) return buckets

  for (const trophy of trophies) {
    const rawValue = rarityForSource(trophy, source)
    const value = rawValue ? parseNumber(rawValue) : null
    if (value === null) continue
    const bucket = buckets.find((candidate) => value <= candidate.maxPercent)
    if (bucket) bucket.count += 1
  }
  return buckets
}

function uniqueGameCount(trophies: Trophy[]): number | null {
  if (trophies.length === 0) return null
  return new Set(trophies.map((trophy) => trophy.game)).size
}

function metricList(
  data: ProfileData,
  gamesPlayed: number | null,
  rarityBuckets: HeroRarityBucket[],
  raritySourceLabel: string | null,
): HeroMetric[] {
  const counts = data.profile_summary.total_trophies
  const stats = data.profile_summary.stats
  const metrics: HeroMetric[] = [
    { key: 'platinum', label: 'Platinum', value: counts.platinum, numeric: true, tone: 'platinum' },
    { key: 'total', label: 'Total trophies', value: counts.total, numeric: true, tone: 'accent' },
  ]
  if (gamesPlayed !== null) {
    metrics.push({
      key: 'games',
      label: 'Games played',
      value: gamesPlayed,
      numeric: true,
      tone: 'text',
    })
  }

  if (stats.Completion) {
    metrics.push({
      key: 'completion',
      label: 'Completion',
      value: stats.Completion,
      numeric: false,
      tone: 'accent',
    })
  } else if (stats.Playtime) {
    metrics.push({
      key: 'playtime',
      label: 'Real playtime',
      value: stats.Playtime,
      numeric: false,
      tone: 'accent',
      detail: 'Official PSN',
    })
  } else {
    const ultraRare = rarityBuckets[0]?.count ?? 0
    if (raritySourceLabel && ultraRare > 0) {
      metrics.push({
        key: 'ultra-rare',
        label: 'Ultra Rare',
        value: ultraRare,
        numeric: true,
        tone: 'accent',
        detail: raritySourceLabel,
      })
    }
  }
  return metrics.slice(0, 4)
}

export function buildOverviewHeroViewModel(data: ProfileData): OverviewHeroViewModel {
  const { profile_summary: summary, trophy_log: trophies } = data
  const source = profileSource(data)
  const raritySource = primaryRaritySource(trophies)
  const raritySourceLabel =
    raritySource === 'psn' ? 'PSN' : raritySource === 'psnprofiles' ? 'PSNP' : null
  const rarityBuckets = buildRarityBuckets(trophies, raritySource)
  const gamesPlayed =
    parseNumber(summary.stats['Games Played']) ?? uniqueGameCount(trophies)
  const total = Math.max(summary.total_trophies.total, 0)
  const trophyMix = GRADE_ORDER.map((grade) => {
    const count = summary.total_trophies[grade.toLowerCase() as keyof TrophyCounts]
    return { grade, count, percentage: total > 0 ? (count / total) * 100 : 0 }
  })
  const recentTrophies = trophies
    .map((trophy) => ({ trophy, earnedAt: parseTrophyTimestamp(trophy.timestamp) }))
    .filter((item): item is RecentTrophyItem => item.earnedAt !== null)
    .sort((left, right) => right.earnedAt.getTime() - left.earnedAt.getTime())
    .slice(0, 4)
  const fetchedAt = data.fetched_at ? new Date(data.fetched_at) : null

  return {
    username: summary.username,
    avatarUrl: summary.avatar_url,
    level: summary.stats.Level?.trim() || null,
    levelProgress: parseNumber(summary.stats['Level Progress']),
    source,
    sourceLabel:
      source === 'psn' ? 'Official PSN' : source === 'psnprofiles' ? 'PSNProfiles' : 'Source unavailable',
    cacheStatus: data.cache_status ?? 'unknown',
    fetchedAt: fetchedAt && !Number.isNaN(fetchedAt.getTime()) ? fetchedAt : null,
    metrics: metricList(data, gamesPlayed, rarityBuckets, raritySourceLabel),
    trophyMix,
    raritySource,
    raritySourceLabel,
    rarityBuckets,
    recentTrophies,
    gamesPlayed,
    completedGames: parseNumber(summary.stats['Completed Games']),
    completionPercent: parseNumber(summary.stats.Completion),
    totalTrophies: total,
  }
}
