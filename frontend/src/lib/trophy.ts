import type { Trophy, TrophyGrade } from './api'

/** CSS var references for each trophy grade, matching the Trophy Gold theme. */
export const GRADE_COLOR_VAR: Record<TrophyGrade, string> = {
  Platinum: 'var(--platinum)',
  Gold: 'var(--gold)',
  Silver: 'var(--silver)',
  Bronze: 'var(--bronze)',
}

/** Parses a rarity string like "2.5%" into a number (2.5). Returns +Infinity if unparseable. */
export function parseRarityPercent(rarityPercent: string): number {
  const value = Number.parseFloat(rarityPercent.replace('%', '').trim())
  return Number.isFinite(value) ? value : Number.POSITIVE_INFINITY
}

/** Returns the `count` trophies with the lowest rarity percentage (rarest first). */
export function getRarestTrophies(trophies: Trophy[], count = 5): Trophy[] {
  return [...trophies]
    .filter((trophy) => Number.isFinite(parseRarityPercent(trophy.rarity_percent)))
    .sort((a, b) => parseRarityPercent(a.rarity_percent) - parseRarityPercent(b.rarity_percent))
    .slice(0, count)
}

// ---------------------------------------------------------------------------
// Timestamp parsing
// ---------------------------------------------------------------------------

const MONTH_INDEX: Record<string, number> = {
  jan: 0,
  feb: 1,
  mar: 2,
  apr: 3,
  may: 4,
  jun: 5,
  jul: 6,
  aug: 7,
  sep: 8,
  oct: 9,
  nov: 10,
  dec: 11,
}

// e.g. "6 Jul 2024 10:11:23 pm" (ordinal suffix already stripped before matching).
const TIMESTAMP_PATTERN =
  /^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(am|pm)$/i

/**
 * Parses a raw trophy timestamp like "6th Jul 2024 10:11:23 pm" into a Date.
 * Robust to the ordinal day suffix and lowercase am/pm used by the scraper.
 * Returns `null` if the string doesn't match the expected shape, including
 * out-of-range components (e.g. day 32) that `Date` would otherwise silently
 * roll over into the next month.
 */
export function parseTrophyTimestamp(raw: string): Date | null {
  const trimmed = raw.trim()
  if (!trimmed) return null

  // ISO-8601 (PSN official-API source), e.g. "2026-07-22T15:21:53+00:00".
  if (/^\d{4}-\d{2}-\d{2}T/.test(trimmed)) {
    const iso = new Date(trimmed)
    return Number.isNaN(iso.getTime()) ? null : iso
  }

  // PSNProfiles scraper format, e.g. "6th Jul 2024 10:11:23 pm".
  const withoutOrdinal = trimmed.replace(/(\d+)(st|nd|rd|th)\b/i, '$1')
  const match = TIMESTAMP_PATTERN.exec(withoutOrdinal)
  if (!match) return null

  const [, dayStr, monthName, yearStr, hourStr, minuteStr, secondStr, meridiem] = match
  const monthIndex = MONTH_INDEX[monthName.slice(0, 3).toLowerCase()]
  if (monthIndex === undefined) return null

  const day = Number.parseInt(dayStr, 10)
  const year = Number.parseInt(yearStr, 10)
  const minute = Number.parseInt(minuteStr, 10)
  const second = Number.parseInt(secondStr, 10)
  let hour = Number.parseInt(hourStr, 10)
  if (hour < 1 || hour > 12) return null

  const isPm = meridiem.toLowerCase() === 'pm'
  if (hour === 12) hour = isPm ? 12 : 0
  else if (isPm) hour += 12

  const date = new Date(year, monthIndex, day, hour, minute, second)
  if (date.getFullYear() !== year || date.getMonth() !== monthIndex || date.getDate() !== day) {
    return null
  }
  return date
}

/** 'YYYY-MM-DD' in local time — a stable, sortable key for day-level grouping. */
export function toDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`
}

/** A trophy with its timestamp successfully parsed into a Date. */
export interface TimestampedTrophy extends Trophy {
  parsedDate: Date
}

/**
 * Attaches a parsed Date to each trophy, dropping rows whose timestamp
 * doesn't parse, sorted ascending by time (oldest first).
 */
export function sortTrophiesByTime(trophies: Trophy[]): TimestampedTrophy[] {
  const parsed: TimestampedTrophy[] = []
  for (const trophy of trophies) {
    const parsedDate = parseTrophyTimestamp(trophy.timestamp)
    if (parsedDate) parsed.push({ ...trophy, parsedDate })
  }
  return parsed.sort((a, b) => a.parsedDate.getTime() - b.parsedDate.getTime())
}

// ---------------------------------------------------------------------------
// Fastest platinums (shared by the Milestones and Games pages)
// ---------------------------------------------------------------------------

export interface FastestPlatinumResult {
  game: string
  durationMs: number
  platinum: TimestampedTrophy
  firstTrophy: TimestampedTrophy
}

/**
 * For each game with a platinum, computes the time from that game's first
 * logged trophy to its platinum. Sorted ascending (fastest first). Games
 * where the computed duration would be negative (out-of-order/bad data) are
 * skipped.
 */
export function getFastestPlatinumsByGame(trophies: Trophy[]): FastestPlatinumResult[] {
  const sorted = sortTrophiesByTime(trophies)
  const firstByGame = new Map<string, TimestampedTrophy>()
  const results: FastestPlatinumResult[] = []

  for (const trophy of sorted) {
    if (!firstByGame.has(trophy.game)) {
      firstByGame.set(trophy.game, trophy)
    }
    if (trophy.grade === 'Platinum') {
      const firstTrophy = firstByGame.get(trophy.game)
      if (firstTrophy) {
        const durationMs = trophy.parsedDate.getTime() - firstTrophy.parsedDate.getTime()
        if (durationMs >= 0) {
          results.push({ game: trophy.game, durationMs, platinum: trophy, firstTrophy })
        }
      }
    }
  }

  return results.sort((a, b) => a.durationMs - b.durationMs)
}

/** Formats a millisecond duration as a compact human string, e.g. "3d 4h". */
export function formatDuration(ms: number): string {
  const totalMinutes = Math.round(ms / 60_000)
  if (totalMinutes < 60) return `${totalMinutes}m`
  const totalHours = Math.floor(totalMinutes / 60)
  if (totalHours < 24) return `${totalHours}h ${totalMinutes % 60}m`
  const days = Math.floor(totalHours / 24)
  return `${days}d ${totalHours % 24}h`
}
