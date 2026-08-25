import type {
  AdvisorCandidate,
  AdvisorBundleResult,
  AdvisorGame,
  AdvisorGameSource,
  AdvisorGameStatus,
  Platform,
  PsnprofilesAdvisorSignals,
} from './api'

export type AdvisorStatusFilter = 'all' | AdvisorGameStatus
export type AdvisorPlatformFilter = 'all' | Extract<Platform, 'PS3' | 'PS4' | 'PS5'>
export type AdvisorSourceFilter = 'all' | AdvisorGameSource
export type AdvisorSortMode =
  | 'library'
  | 'name'
  | 'progress'
  | 'playtime'
  | 'platinumAchievers'
  | 'platinumRate'
  | 'score'

export interface AdvisorWeights {
  platinumRate: number
  platinumAchievers: number
}

export interface AdvisorFilters {
  search: string
  status: AdvisorStatusFilter
  platform: AdvisorPlatformFilter
  source: AdvisorSourceFilter
}

function candidateNames(game: AdvisorGame): string[] {
  const values = [game.trophy_title, game.name]
    .map((value) => value?.trim() ?? '')
    .filter(Boolean)
    .filter(
      (value, index, all) =>
        all.findIndex((candidate) => candidate.toLocaleLowerCase() === value.toLocaleLowerCase()) ===
        index,
    )

  // Sony can return a localized library name and a different trophy-set name.
  // Prefer a Latin/English source title when one already exists; never translate
  // or replace the title displayed to the user.
  return values
    .map((value, index) => ({
      value,
      index,
      english:
        /[A-Za-z]{3}/.test(value) && !/[\u3400-\u9fff\uf900-\ufaff]/u.test(value),
    }))
    .sort((left, right) => Number(right.english) - Number(left.english) || left.index - right.index)
    .map(({ value }) => value)
}

export function advisorCandidateName(game: AdvisorGame): string {
  return candidateNames(game)[0] || game.name
}

export function advisorSignalKey(game: string, platform?: Platform | null): string {
  return `${game.trim().toLocaleLowerCase()}\u0000${platform ?? 'UNKNOWN'}`
}

export function advisorCandidateKey(game: AdvisorGame): string {
  return advisorSignalKey(advisorCandidateName(game), game.platform)
}

export function toAdvisorCandidate(game: AdvisorGame): AdvisorCandidate {
  const [name, ...aliases] = candidateNames(game)
  return {
    game: name || game.name,
    platform: game.platform,
    title_id: game.title_id,
    product_id: game.product_id,
    ...(aliases.length > 0 ? { aliases } : {}),
  }
}

export function filterAdvisorGames(
  games: AdvisorGame[],
  filters: AdvisorFilters,
): AdvisorGame[] {
  const query = filters.search.trim().toLocaleLowerCase()
  return games.filter((game) => {
    if (filters.status !== 'all' && game.status !== filters.status) return false
    if (
      filters.platform !== 'all' &&
      !(game.available_platforms.length > 0
        ? game.available_platforms.includes(filters.platform)
        : game.platform === filters.platform)
    ) return false
    if (filters.source !== 'all' && game.source !== filters.source) return false
    return !query || game.name.toLocaleLowerCase().includes(query)
  })
}

export function advisorScore(
  signals: PsnprofilesAdvisorSignals | undefined,
  maxPlatinumAchievers: number,
  weights: AdvisorWeights,
): number | null {
  if (!signals) return null
  const platinumRate = signals.platinum_rate
  const platinumAchievers =
    signals.platinum_achievers != null &&
    signals.platinum_achievers >= 0 &&
    maxPlatinumAchievers > 0
      ? Math.log1p(signals.platinum_achievers) / Math.log1p(maxPlatinumAchievers)
      : null

  let weighted = 0
  let availableWeight = 0
  if (platinumRate != null) {
    weighted +=
      (Math.min(100, Math.max(0, platinumRate)) / 100) * weights.platinumRate
    availableWeight += weights.platinumRate
  }
  if (platinumAchievers != null) {
    weighted += platinumAchievers * weights.platinumAchievers
    availableWeight += weights.platinumAchievers
  }
  return availableWeight > 0 ? (weighted / availableWeight) * 100 : null
}

function nullableNumber(value: number | null | undefined, descending = true): number {
  if (value == null || !Number.isFinite(value)) {
    return descending ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY
  }
  return value
}

export function sortAdvisorGames(
  games: AdvisorGame[],
  sortMode: AdvisorSortMode,
  signalsByKey: ReadonlyMap<string, PsnprofilesAdvisorSignals>,
  weights: AdvisorWeights,
  bundlesByKey: ReadonlyMap<string, AdvisorBundleResult> = new Map(),
): AdvisorGame[] {
  const bundleSignals = Array.from(bundlesByKey.values()).flatMap((bundle) =>
    bundle.children.flatMap((child) => child.signals ? [child.signals] : []),
  )
  const maxPlatinumAchievers = Math.max(
    0,
    ...Array.from(signalsByKey.values(), (signals) => signals.platinum_achievers ?? 0),
    ...bundleSignals.map((signals) => signals.platinum_achievers ?? 0),
  )
  const signalsFor = (game: AdvisorGame): PsnprofilesAdvisorSignals[] => {
    const key = advisorCandidateKey(game)
    const direct = signalsByKey.get(key)
    if (direct) return [direct]
    return (bundlesByKey.get(key)?.children ?? [])
      .flatMap((child) => child.signals ? [child.signals] : [])
  }
  const maximum = (
    game: AdvisorGame,
    value: (signals: PsnprofilesAdvisorSignals) => number | null,
  ): number | null => {
    const values = signalsFor(game)
      .map(value)
      .filter((item): item is number => item != null)
    return values.length > 0 ? Math.max(...values) : null
  }
  return [...games].sort((left, right) => {
    let difference = 0
    if (sortMode === 'name') return left.name.localeCompare(right.name)
    if (sortMode === 'progress') {
      difference = nullableNumber(right.progress) - nullableNumber(left.progress)
    } else if (sortMode === 'playtime') {
      difference = nullableNumber(right.playtime_seconds) - nullableNumber(left.playtime_seconds)
    } else if (sortMode === 'platinumAchievers') {
      difference =
        nullableNumber(maximum(right, (signals) => signals.platinum_achievers)) -
        nullableNumber(maximum(left, (signals) => signals.platinum_achievers))
    } else if (sortMode === 'platinumRate') {
      difference =
        nullableNumber(maximum(right, (signals) => signals.platinum_rate)) -
        nullableNumber(maximum(left, (signals) => signals.platinum_rate))
    } else if (sortMode === 'score') {
      difference =
        nullableNumber(maximum(right, (signals) => advisorScore(signals, maxPlatinumAchievers, weights))) -
        nullableNumber(maximum(left, (signals) => advisorScore(signals, maxPlatinumAchievers, weights)))
    }
    return difference || left.library_index - right.library_index
  })
}
