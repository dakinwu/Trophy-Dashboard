export function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-16 text-center">
      <h1 className="text-xl font-semibold text-text">Page not found</h1>
      <p className="text-sm text-muted">The page you're looking for doesn't exist.</p>
    </div>
  )
}
