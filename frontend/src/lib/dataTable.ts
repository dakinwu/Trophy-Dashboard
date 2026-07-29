import type { Trophy, TrophyGrade } from './api'
import { toCsv } from './csv'
import { formatTrophyRarity, parseTrophyTimestamp, toDateKey } from './trophy'

export interface DataRow extends Trophy {
  parsedDate: Date | null
}

/**
 * Attaches a (possibly null) parsed Date to every trophy and sorts newest first.
 * Unparseable timestamps are retained at the end of the table.
 */
export function toDataRows(trophies: Trophy[]): DataRow[] {
  return trophies
    .map((trophy) => ({
      ...trophy,
      parsedDate: parseTrophyTimestamp(trophy.timestamp),
    }))
    .sort((a, b) => {
      if (!a.parsedDate && !b.parsedDate) return 0
      if (!a.parsedDate) return 1
      if (!b.parsedDate) return -1
      return b.parsedDate.getTime() - a.parsedDate.getTime()
    })
}

export const ALL_GRADES: TrophyGrade[] = ['Platinum', 'Gold', 'Silver', 'Bronze']

export interface DataFilters {
  search: string
  grades: Set<TrophyGrade>
  /** 'YYYY-MM-DD', inclusive; '' means unset. */
  from: string
  /** 'YYYY-MM-DD', inclusive; '' means unset. */
  to: string
}

export function createDefaultFilters(): DataFilters {
  return { search: '', grades: new Set(ALL_GRADES), from: '', to: '' }
}

/**
 * Applies game-name search, grade multi-select, and date-range filters.
 * Rows whose timestamp didn't parse are excluded whenever a date-range
 * filter is active, since we can't tell if they fall inside the range.
 */
export function filterDataRows(rows: DataRow[], filters: DataFilters): DataRow[] {
  const search = filters.search.trim().toLowerCase()
  const fromKey = filters.from || null
  const toKey = filters.to || null

  return rows.filter((row) => {
    if (!filters.grades.has(row.grade)) return false
    if (search && !row.game.toLowerCase().includes(search)) return false

    if (fromKey || toKey) {
      if (!row.parsedDate) return false
      const key = toDateKey(row.parsedDate)
      if (fromKey && key < fromKey) return false
      if (toKey && key > toKey) return false
    }

    return true
  })
}

/** Serializes rows to CSV (Game, Trophy, Date, Grade, Rarity). */
export function dataRowsToCsv(rows: DataRow[]): string {
  const header = ['Game', 'Trophy', 'Date', 'Grade', 'Rarity']
  const body = rows.map((row) => [
    row.game,
    row.title,
    row.parsedDate ? row.parsedDate.toISOString() : row.timestamp,
    row.grade,
    formatTrophyRarity(row),
  ])
  return toCsv(header, body)
}
