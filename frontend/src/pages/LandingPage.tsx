import { Button, Input } from '@heroui/react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

/** Empty state shown at `/` before a PSN ID has been searched. */
export function LandingPage() {
  const [value, setValue] = useState('')
  const navigate = useNavigate()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) return
    navigate(`/u/${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 rounded-2xl border border-border bg-surface p-12 text-center">
      <span className="text-5xl" aria-hidden="true">
        🏆
      </span>
      <div>
        <h1 className="text-2xl font-semibold text-text">獎盃獵人儀表板</h1>
        <p className="mt-2 max-w-md text-sm text-muted">
          輸入 PlayStation Network ID，查看獎盃歷程、稀有度與里程碑。
        </p>
      </div>
      <form onSubmit={handleSubmit} className="flex w-full max-w-sm gap-2">
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="輸入 PSN ID…"
          aria-label="PSN ID"
          variant="secondary"
          fullWidth
          className="min-w-0 flex-1"
        />
        <Button
          type="submit"
          variant="primary"
          className="shrink-0"
        >
          查詢
        </Button>
      </form>
    </div>
  )
}
