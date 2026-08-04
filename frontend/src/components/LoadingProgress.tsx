import { Spinner } from './Spinner'

/**
 * Loading indicator shown while the profile query is in flight. The data comes
 * from the cached `GET /api/profile/{username}` request (react-query); we no
 * longer open the SSE stream here, which used to force a fresh re-fetch on
 * every load.
 */
export function LoadingProgress({ username }: { username: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-10 text-center">
      <Spinner />
      <p className="magic-shimmer-text text-sm font-medium">Fetching {username}'s trophies…</p>
    </div>
  )
}
