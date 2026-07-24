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
