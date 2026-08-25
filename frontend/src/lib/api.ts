/**
 * Typed fetch client for the Trophy Hunter Dashboard backend.
 *
 * All requests go through the `/api/*` prefix, which Vite's dev server
 * proxies to http://localhost:8000 (see vite.config.ts). In production this
 * assumes the same-origin API is reverse-proxied under `/api`.
 */

export interface TrophyCounts {
  total: number
  platinum: number
  gold: number
  silver: number
  bronze: number
}

export interface ProfileSummary {
  username: string
  avatar_url: string | null
  total_trophies: TrophyCounts
  /** Keys vary by profile (e.g. "Level", "Completion") — render generically. */
  stats: Record<string, string>
}

export type TrophyGrade = 'Platinum' | 'Gold' | 'Silver' | 'Bronze'
export type RaritySource = 'psn' | 'psnprofiles' | 'unknown'
export type Platform = 'PS3' | 'PS4' | 'PS5' | 'PSVITA' | 'PSPC' | 'UNKNOWN'

export interface Trophy {
  game: string
  platforms?: Platform[]
  icon_url: string
  title: string
  description?: string | null
  /** Raw string, e.g. "6th Jul 2024 10:11:23 pm" — not parsed here. */
  timestamp: string
  earned?: boolean
  /** Raw string, e.g. "2.5%". */
  rarity_percent: string
  rarity_source?: RaritySource
  rarity_label?: string | null
  psn_rarity_percent?: string | null
  psnprofiles_rarity_percent?: string | null
  grade: TrophyGrade
  trophy_id?: number | null
  is_dlc?: boolean
}

export interface ProfileData {
  profile_summary: ProfileSummary
  trophy_log: Trophy[]
  platinum_games?: PlatinumGame[]
  summary_only?: boolean
  profile_source?: 'psn' | 'psnprofiles' | null
  cache_status?: 'live' | 'cached' | null
  fetched_at?: string | null
  /** Game title -> real playtime in seconds (PSN API source only). */
  game_playtime_seconds?: Record<string, number>
}

export interface PlatinumGame {
  game: string
  platforms: Platform[]
  icon_url: string
}

export interface GameTrophyDetail {
  game: string
  display_name: string
  platforms: Platform[]
  trophies: Trophy[]
  complete: boolean
  source: 'psn' | 'psnprofiles' | 'profile_log'
}

export interface HealthStatus {
  status: string
}

/** Thrown for any non-2xx response from the API. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === 'object') {
      const record = body as Record<string, unknown>
      if (typeof record.detail === 'string') return record.detail
      if (typeof record.error === 'string') return record.error
      if (record.detail !== undefined) return JSON.stringify(record.detail)
    }
  } catch {
    // response wasn't JSON — fall through to statusText
  }
  return res.statusText || `Request failed with status ${res.status}`
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorMessage(res))
  }
  return (await res.json()) as T
}

export function getHealth(): Promise<HealthStatus> {
  return requestJson<HealthStatus>('/api/health')
}

export function getProfile(username: string, refresh = false): Promise<ProfileData> {
  const params = new URLSearchParams()
  if (refresh) params.set('refresh', 'true')
  const qs = params.toString()
  const url = `/api/profile/${encodeURIComponent(username)}${qs ? `?${qs}` : ''}`
  return requestJson<ProfileData>(url)
}

export function getAdvisorLibrary(
  username: string,
  refresh = false,
): Promise<AdvisorLibrary> {
  const params = new URLSearchParams()
  if (refresh) params.set('refresh', 'true')
  const qs = params.toString()
  return requestJson<AdvisorLibrary>(
    `/api/profile/${encodeURIComponent(username)}/advisor${qs ? `?${qs}` : ''}`,
  )
}

export function getAdvisorSignals(
  candidates: AdvisorCandidate[],
  cachedOnly = false,
): Promise<AdvisorBatchResponse> {
  const suffix = cachedOnly ? '?cached_only=true' : ''
  return requestJson<AdvisorBatchResponse>(`/api/psnprofiles/advisor${suffix}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidates }),
  })
}

export function getGameDetail(username: string, game: string): Promise<GameTrophyDetail> {
  const params = new URLSearchParams({ game })
  return requestJson<GameTrophyDetail>(
    `/api/profile/${encodeURIComponent(username)}/game?${params.toString()}`,
  )
}

export interface HltbTimes {
  game_name: string
  main_story: number
  main_extra: number
  completionist: number
}

/** HowLongToBeat completion times for a game; null if not found. */
export async function getHltb(game: string): Promise<HltbTimes | null> {
  const res = await fetch(`/api/hltb?game=${encodeURIComponent(game)}`)
  if (!res.ok) return null
  const data = (await res.json()) as Partial<HltbTimes>
  return typeof data?.main_story === 'number' ? (data as HltbTimes) : null
}

export interface PsnprofilesGuide {
  title: string | null
  guide_url: string
  difficulty: string | null
  platinum_time: string | null
}

/** On-demand PSNProfiles trophy-guide metadata; null if no guide was found. */
export async function getPsnprofilesGuide(game: string): Promise<PsnprofilesGuide | null> {
  const res = await fetch(`/api/psnprofiles/guide?game=${encodeURIComponent(game)}`)
  if (!res.ok) return null
  const data = (await res.json()) as Partial<PsnprofilesGuide>
  return typeof data?.guide_url === 'string' ? (data as PsnprofilesGuide) : null
}

export interface PsnprofilesStats {
  world_rank: number | null
  country_rank: number | null
  country_label: string | null
  completion: string | null
  profile_url: string
}

export interface PsnprofilesTrophy {
  trophy_id: number | null
  title: string
  psnprofiles_rarity_percent: string | null
  rarity_percentages?: string[]
  rarity_label: string | null
  trophy_url: string
}

export interface PsnprofilesTrophyList {
  title: string
  platform: string
  game_url: string
  trophies: PsnprofilesTrophy[]
  owners?: number | null
  average_completion?: number | null
  platinum_achievers?: number | null
  platinum_rate?: number | null
}

export type AdvisorGameStatus = 'unplayed' | 'in_progress' | 'completed'
export type AdvisorGameSource = 'purchased' | 'ps_plus' | 'other'
export type AdvisorAutopopStatus = 'full' | 'partial' | 'none' | 'unknown'

export interface AdvisorGame {
  title_id: string
  product_id: string | null
  concept_id: string | null
  name: string
  platform: Platform
  available_platforms: Platform[]
  image_url: string | null
  source: AdvisorGameSource
  is_downloadable: boolean
  is_preorder: boolean
  library_index: number
  played: boolean
  status: AdvisorGameStatus
  progress: number | null
  playtime_seconds: number | null
  earned_trophies: number | null
  defined_trophies: number | null
  earned_platinum: number | null
  trophy_title: string | null
  ps4_platinum_earned: boolean
  ps4_to_ps5_autopop: AdvisorAutopopStatus | null
  autopop_note: string | null
  autopop_source_url: string | null
  autopop_verified_at: string | null
}

export interface AdvisorLibrary {
  username: string
  games: AdvisorGame[]
  total_count: number
  unplayed_count: number
  in_progress_count: number
  completed_count: number
  excluded_trial_count: number
  excluded_content_count: number
  excluded_platinum_count: number
  merged_platform_count: number
  cache_status: 'live' | 'cached'
  fetched_at: string | null
  source: 'official_psn'
  title_resolver: 'gemini' | 'source_title'
}

export interface AdvisorCandidate {
  game: string
  platform?: Platform | null
  aliases?: string[]
  title_id?: string | null
  product_id?: string | null
}

export interface PsnprofilesAdvisorSignals {
  title: string
  platform: string
  game_url: string
  owners: number | null
  average_completion: number | null
  platinum_achievers: number | null
  platinum_rate: number | null
}

export interface AdvisorBundleChildResult {
  game: string
  platform: Platform | null
  signals: PsnprofilesAdvisorSignals | null
  error: string | null
}

export interface AdvisorBundleResult {
  source: 'curated' | 'gemini_grounding'
  source_urls: string[]
  verified_at: string
  children: AdvisorBundleChildResult[]
  complete: boolean
}

export interface AdvisorSignalResult {
  game: string
  platform: Platform | null
  signals: PsnprofilesAdvisorSignals | null
  bundle: AdvisorBundleResult | null
  error: string | null
  retryable: boolean
}

export interface AdvisorBatchResponse {
  results: AdvisorSignalResult[]
}

/** On-demand PSNProfiles rankings; null if the profile is unavailable. */
export async function getPsnprofilesStats(username: string): Promise<PsnprofilesStats | null> {
  const res = await fetch(`/api/psnprofiles/stats?username=${encodeURIComponent(username)}`)
  if (!res.ok) return null
  const data = (await res.json()) as Partial<PsnprofilesStats>
  return typeof data?.profile_url === 'string' ? (data as PsnprofilesStats) : null
}

/** On-demand PSNProfiles rarity data for one exact title/platform. */
export async function getPsnprofilesTrophies(
  game: string,
  platform?: Platform,
): Promise<PsnprofilesTrophyList | null> {
  const params = new URLSearchParams({ game })
  if (platform && platform !== 'UNKNOWN') params.set('platform', platform)
  const res = await fetch(`/api/psnprofiles/trophies?${params.toString()}`)
  if (!res.ok) return null
  const data = (await res.json()) as Partial<PsnprofilesTrophyList>
  return typeof data?.game_url === 'string' && Array.isArray(data.trophies)
    ? (data as PsnprofilesTrophyList)
    : null
}

// ---------------------------------------------------------------------------
// SSE stream: GET /api/profile/{username}/stream
// ---------------------------------------------------------------------------

export interface StreamProgressEvent {
  page: number
  total: number
}

export interface StreamDoneEvent {
  found: boolean
}

export interface StreamErrorEvent {
  error: string
}

export interface ProfileStreamHandlers {
  onProgress?: (data: StreamProgressEvent) => void
  onDone?: (data: StreamDoneEvent) => void
  onError?: (data: StreamErrorEvent) => void
  /** Fired on a transport-level failure (e.g. connection dropped). */
  onConnectionError?: () => void
}

/**
 * Subscribes to the scrape-progress SSE stream for a username.
 * Returns an unsubscribe function that closes the connection.
 */
export function subscribeToProfileStream(
  username: string,
  handlers: ProfileStreamHandlers,
): () => void {
  const source = new EventSource(`/api/profile/${encodeURIComponent(username)}/stream`)

  const handleProgress = (event: MessageEvent<string>) => {
    try {
      handlers.onProgress?.(JSON.parse(event.data) as StreamProgressEvent)
    } catch {
      // ignore malformed progress payloads
    }
  }

  const handleDone = (event: MessageEvent<string>) => {
    try {
      handlers.onDone?.(JSON.parse(event.data) as StreamDoneEvent)
    } catch {
      handlers.onDone?.({ found: false })
    }
    source.close()
  }

  // Note: EventSource dispatches both transport-level failures and a
  // server-sent `event: error` under the same "error" type. Distinguish by
  // whether the event carries `data` (MessageEvent) or not (plain Event).
  const handleErrorEvent = (event: Event) => {
    if (event instanceof MessageEvent && typeof event.data === 'string') {
      try {
        handlers.onError?.(JSON.parse(event.data) as StreamErrorEvent)
      } catch {
        handlers.onError?.({ error: '未知的串流錯誤' })
      }
      source.close()
      return
    }
    handlers.onConnectionError?.()
    source.close()
  }

  source.addEventListener('progress', handleProgress)
  source.addEventListener('done', handleDone)
  source.addEventListener('error', handleErrorEvent)

  return () => {
    source.removeEventListener('progress', handleProgress)
    source.removeEventListener('done', handleDone)
    source.removeEventListener('error', handleErrorEvent)
    source.close()
  }
}
