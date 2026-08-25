import type { Trophy } from './api'
import { sortTrophiesByTime, toDateKey } from './trophy'

export interface MonthlyGradeCounts {
  monthKey: string
  monthLabel: string
  Platinum: number
  Gold: number
  Silver: number
  Bronze: number
}

/** Trophies earned per calendar month, stacked by grade, in chronological order. */
export function getMonthlyGradeCounts(trophies: Trophy[]): MonthlyGradeCounts[] {
  const byMonth = new Map<string, MonthlyGradeCounts>()

  for (const trophy of sortTrophiesByTime(trophies)) {
    const key = `${trophy.parsedDate.getFullYear()}-${String(
      trophy.parsedDate.getMonth() + 1,
    ).padStart(2, '0')}`
    let entry = byMonth.get(key)
    if (!entry) {
      entry = {
        monthKey: key,
        monthLabel: trophy.parsedDate.toLocaleDateString('zh-TW', {
          month: 'short',
          year: 'numeric',
        }),
        Platinum: 0,
        Gold: 0,
        Silver: 0,
        Bronze: 0,
      }
      byMonth.set(key, entry)
    }
    entry[trophy.grade] += 1
  }

  return [...byMonth.values()].sort((a, b) => a.monthKey.localeCompare(b.monthKey))
}

/** Maps 'YYYY-MM-DD' -> number of trophies earned that day. */
export function getDailyActivityMap(trophies: Trophy[]): Map<string, number> {
  const map = new Map<string, number>()
  for (const trophy of sortTrophiesByTime(trophies)) {
    const key = toDateKey(trophy.parsedDate)
    map.set(key, (map.get(key) ?? 0) + 1)
  }
  return map
}

/** Distinct years with at least one trophy, most recent first. */
export function getActivityYears(dailyActivity: Map<string, number>): number[] {
  const years = new Set<number>()
  for (const key of dailyActivity.keys()) {
    years.add(Number.parseInt(key.slice(0, 4), 10))
  }
  return [...years].sort((a, b) => b - a)
}

export interface StreakStats {
  longest: number
  current: number
}

const ONE_DAY_MS = 86_400_000

/**
 * Longest and current streaks of consecutive days with >=1 trophy earned.
 * "Current" is measured relative to the most recent day present in the log
 * (not wall-clock today) — the log's own recency is what determines whether
 * a streak is still open for that data.
 */
export function getStreakStats(dailyActivity: Map<string, number>): StreakStats {
  if (dailyActivity.size === 0) return { longest: 0, current: 0 }

  const times = [...dailyActivity.keys()].sort().map(dateKeyToUTCTime)

  let longest = 1
  let running = 1
  for (let i = 1; i < times.length; i++) {
    running = times[i] - times[i - 1] === ONE_DAY_MS ? running + 1 : 1
    longest = Math.max(longest, running)
  }

  let current = 1
  for (let i = times.length - 1; i > 0; i--) {
    if (times[i] - times[i - 1] === ONE_DAY_MS) current += 1
    else break
  }

  return { longest, current }
}

function dateKeyToUTCTime(key: string): number {
  const [year, month, day] = key.split('-').map(Number)
  return Date.UTC(year, month - 1, day)
}

/** Buckets a day's count into a 0-4 intensity level relative to the year's max, for heatmap coloring. */
export function getHeatmapLevel(count: number, max: number): number {
  if (count <= 0 || max <= 0) return 0
  const ratio = count / max
  if (ratio > 0.75) return 4
  if (ratio > 0.5) return 3
  if (ratio > 0.25) return 2
  return 1
}
