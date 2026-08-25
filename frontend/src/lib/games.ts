import type { Platform, Trophy, TrophyGrade } from './api'
import { parseRarityPercent, sortTrophiesByTime } from './trophy'

export interface GameSummary {
  /** Source game key, including a platform suffix when needed for uniqueness. */
  game: string
  /** Human-facing title; platform is represented by logos instead of a suffix. */
  displayName: string
  platforms: Platform[]
  iconUrl: string
  counts: Record<TrophyGrade, number>
  totalEarned: number
  hasPlatinum: boolean
  lastEarnedDate: Date | null
  /** Real playtime in seconds (PSN API source), or null if unknown. */
  playtimeSeconds: number | null
}

const ICON_GRADE_PRIORITY: Record<TrophyGrade, number> = {
  Platinum: 0,
  Gold: 1,
  Silver: 2,
  Bronze: 3,
}

function displayGameName(game: string): string {
  return game.replace(/\s+\((?:PS3|PS4|PS5|PS\s*VITA|PSVITA|PSPC)\)\s*$/i, '')
}

/** Groups the trophy log by game, sorted by total trophies earned (descending). */
export function groupTrophiesByGame(
  trophies: Trophy[],
  playtimeByGame: Record<string, number> = {},
): GameSummary[] {
  const byGame = new Map<string, GameSummary>()
  const iconPriority = new Map<string, number>()

  for (const trophy of trophies) {
    const trophyPlatforms: Platform[] =
      trophy.platforms && trophy.platforms.length > 0 ? trophy.platforms : ['UNKNOWN']
    let summary = byGame.get(trophy.game)
    if (!summary) {
      summary = {
        game: trophy.game,
        displayName: displayGameName(trophy.game),
        platforms: [...new Set<Platform>(trophyPlatforms)],
        iconUrl: trophy.icon_url,
        counts: { Platinum: 0, Gold: 0, Silver: 0, Bronze: 0 },
        totalEarned: 0,
        hasPlatinum: false,
        lastEarnedDate: null,
        playtimeSeconds: playtimeByGame[trophy.game] ?? null,
      }
      byGame.set(trophy.game, summary)
      iconPriority.set(trophy.game, ICON_GRADE_PRIORITY[trophy.grade])
    }

    for (const platform of trophyPlatforms) {
      if (!summary.platforms.includes(platform)) summary.platforms.push(platform)
    }
    summary.counts[trophy.grade] += 1
    summary.totalEarned += 1
    if (trophy.grade === 'Platinum') summary.hasPlatinum = true

    // Prefer showing the rarest-grade icon available as the game's stand-in icon.
    const currentPriority = iconPriority.get(trophy.game) ?? Number.POSITIVE_INFINITY
    if (ICON_GRADE_PRIORITY[trophy.grade] < currentPriority) {
      summary.iconUrl = trophy.icon_url
      iconPriority.set(trophy.game, ICON_GRADE_PRIORITY[trophy.grade])
    }
  }

  for (const trophy of sortTrophiesByTime(trophies)) {
    const summary = byGame.get(trophy.game)
    if (summary) summary.lastEarnedDate = trophy.parsedDate
  }

  return [...byGame.values()].sort((a, b) => b.totalEarned - a.totalEarned)
}

export interface RarityBucket {
  label: string
  count: number
}

const RARITY_BUCKETS: { label: string; max: number }[] = [
  { label: '極度稀有', max: 5 },
  { label: '非常稀有', max: 10 },
  { label: '稀有', max: 20 },
  { label: '不常見', max: 50 },
  { label: '常見', max: Number.POSITIVE_INFINITY },
]

/** Buckets earned trophies by rarity percent: Ultra <=5%, Very <=10%, Rare <=20%, Uncommon <=50%, Common >50%. */
export function getRarityDistribution(trophies: Trophy[]): RarityBucket[] {
  const buckets = RARITY_BUCKETS.map((bucket) => ({ label: bucket.label, count: 0 }))

  for (const trophy of trophies) {
    const percent = parseRarityPercent(trophy.rarity_percent)
    if (!Number.isFinite(percent)) continue
    const index = RARITY_BUCKETS.findIndex((bucket) => percent <= bucket.max)
    if (index !== -1) buckets[index].count += 1
  }

  return buckets
}

export interface TopGameSlice {
  game: string
  total: number
}

/** Top `count` games by total trophies earned. */
export function getTopGamesByTrophies(summaries: GameSummary[], count = 8): TopGameSlice[] {
  return [...summaries]
    .sort((a, b) => b.totalEarned - a.totalEarned)
    .slice(0, count)
    .map((summary) => ({ game: summary.game, total: summary.totalEarned }))
}

/** Formats a playtime in seconds as a compact string, e.g. "241h" or "45m". */
export function formatPlaytime(seconds: number): string {
  if (seconds >= 3600) return `${Math.round(seconds / 3600).toLocaleString()} 小時`
  if (seconds >= 60) return `${Math.round(seconds / 60)} 分鐘`
  return `${Math.round(seconds)} 秒`
}
