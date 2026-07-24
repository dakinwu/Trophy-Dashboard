/** Themed placeholder for the Games / Timeline / Milestones / Data pages (Chunk B+). */
export function ComingNextPage({ title }: { title: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface/60 p-16 text-center">
      <span className="text-3xl" aria-hidden="true">
        🚧
      </span>
      <h1 className="text-xl font-semibold text-text">{title}</h1>
      <p className="text-sm text-muted">Coming next.</p>
    </div>
  )
}
