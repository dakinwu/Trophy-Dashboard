import { useEffect, useState } from 'react'
import { subscribeToProfileStream, type StreamProgressEvent } from '../lib/api'
import { Spinner } from './Spinner'

/**
 * Loading indicator shown while the profile query is in flight. Subscribes to
 * the SSE progress stream purely for a nicer message; the actual data comes
 * from the GET /api/profile/{username} request driven by react-query.
 */
export function LoadingProgress({ username }: { username: string }) {
  const [progress, setProgress] = useState<StreamProgressEvent | null>(null)

  useEffect(() => {
    setProgress(null)
    const unsubscribe = subscribeToProfileStream(username, {
      onProgress: setProgress,
    })
    return unsubscribe
  }, [username])

  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-10 text-center">
      <Spinner />
      <p className="text-sm text-muted">
        {progress
          ? `Fetching trophy page ${progress.page} of ${progress.total}…`
          : `Fetching ${username}'s trophies…`}
      </p>
    </div>
  )
}
