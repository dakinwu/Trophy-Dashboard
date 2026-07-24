export function ErrorState({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-border bg-surface p-10 text-center">
      <span className="text-3xl" aria-hidden="true">
        ⚠️
      </span>
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      <p className="max-w-md text-sm text-muted">{message}</p>
    </div>
  )
}
