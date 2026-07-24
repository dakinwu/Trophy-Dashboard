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

export interface Trophy {
  game: string
  icon_url: string
  title: string
  /** Raw string, e.g. "6th Jul 2024 10:11:23 pm" — not parsed here. */
  timestamp: string
  /** Raw string, e.g. "2.5%". */
  rarity_percent: string
  grade: TrophyGrade
}

export interface ProfileData {
  profile_summary: ProfileSummary
  trophy_log: Trophy[]
  /** Game title -> real playtime in seconds (PSN API source only). */
  game_playtime_seconds?: Record<string, number>
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

async function requestJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
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
        handlers.onError?.({ error: 'Unknown stream error' })
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
