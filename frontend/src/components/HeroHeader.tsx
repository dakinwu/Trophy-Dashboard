import type { ProfileSummary } from '../lib/api'

export function HeroHeader({ summary }: { summary: ProfileSummary }) {
  const statEntries = Object.entries(summary.stats ?? {}).slice(0, 3)

  return (
    <section className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-surface p-6 shadow-lg shadow-black/20 sm:flex-row sm:text-left">
      {summary.avatar_url ? (
        <img
          src={summary.avatar_url}
          alt={`${summary.username} avatar`}
          className="h-20 w-20 shrink-0 rounded-full border-2 border-accent bg-bg object-cover"
        />
      ) : (
        <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-2 border-accent bg-bg text-3xl">
          🏆
        </div>
      )}

      <div className="min-w-0">
        <h1 className="truncate text-2xl font-semibold text-text">{summary.username}</h1>
        {statEntries.length > 0 && (
          <p className="mt-1 flex flex-wrap justify-center gap-x-2 text-sm text-muted sm:justify-start">
            {statEntries.map(([label, value], index) => (
              <span key={label}>
                {index > 0 && <span className="mr-2 text-border">•</span>}
                {label}: <span className="text-text">{value}</span>
              </span>
            ))}
          </p>
        )}
      </div>
    </section>
  )
}
