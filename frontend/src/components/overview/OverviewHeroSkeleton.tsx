import { Skeleton } from '@heroui/react'

export function OverviewHeroSkeleton({ username }: { username: string }) {
  return (
    <section
      className="overflow-hidden rounded-3xl border border-border bg-surface p-5 shadow-xl shadow-black/20 sm:p-6"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
        <div>
          <div className="flex items-center gap-4">
            <Skeleton className="h-20 w-20 shrink-0 rounded-2xl" />
            <div className="min-w-0 flex-1">
              <Skeleton className="h-3 w-28 rounded-full" />
              <Skeleton className="mt-3 h-7 w-52 max-w-full rounded-lg" />
              <Skeleton className="mt-3 h-4 w-40 rounded-full" />
            </div>
          </div>
          <div className="mt-6 flex items-center gap-5">
            <Skeleton className="h-32 w-32 shrink-0 rounded-full" />
            <div className="grid flex-1 grid-cols-2 gap-2">
              {[0, 1, 2, 3].map((item) => (
                <Skeleton key={item} className="h-20 rounded-xl" />
              ))}
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[0, 1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-11 rounded-xl" />
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-bg/35 p-4">
          <div className="flex gap-2">
            {[0, 1, 2].map((item) => (
              <Skeleton key={item} className="h-9 flex-1 rounded-lg" />
            ))}
          </div>
          <Skeleton className="mt-5 h-52 rounded-xl" />
        </div>
      </div>
      <div className="mt-5 border-t border-border/60 pt-4">
        <p className="text-sm font-medium text-text">Loading {username}'s profile and trophy library…</p>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">
          First-time public profile lookups can take longer and may open a visible Chrome window
          while PSNProfiles is being accessed.
        </p>
      </div>
    </section>
  )
}
