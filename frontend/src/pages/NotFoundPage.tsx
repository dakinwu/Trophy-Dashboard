export function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-surface p-16 text-center">
      <h1 className="text-xl font-semibold text-text">找不到頁面</h1>
      <p className="text-sm text-muted">你要前往的頁面不存在。</p>
    </div>
  )
}
