import { Button, Input } from '@heroui/react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, useMatch, useNavigate } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Overview', subpath: '' },
  { label: 'Games', subpath: '/games' },
  { label: 'Timeline', subpath: '/timeline' },
  { label: 'Milestones', subpath: '/milestones' },
  { label: 'Data', subpath: '/data' },
]

/**
 * Top navigation bar: brand, PSN-ID search, and section links.
 * The active username is derived from the URL (`/u/:username/*`) rather than
 * useParams, since this component sits outside the routed page it names.
 */
export function TopNav() {
  const match = useMatch('/u/:username/*')
  const username = match?.params.username
  const navigate = useNavigate()
  const [query, setQuery] = useState(username ?? '')

  useEffect(() => {
    setQuery(username ?? '')
  }, [username])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    navigate(`/u/${encodeURIComponent(trimmed)}`)
  }

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3 sm:gap-4 sm:px-6">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2 text-lg font-semibold text-text"
        >
          <span aria-hidden="true">🏆</span>
          <span>Trophy Hunter</span>
        </Link>

        <form
          onSubmit={handleSubmit}
          className="order-3 flex w-full min-w-0 basis-full grow items-center gap-2 sm:order-none sm:w-auto sm:basis-0 sm:min-w-[200px]"
        >
          <Input
            id="global-psn-id-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="PSN ID..."
            aria-label="PSN ID"
            variant="secondary"
            fullWidth
            className="min-w-0 flex-1"
          />
          <Button
            type="submit"
            size="sm"
            variant="primary"
            className="shrink-0"
          >
            Analyze
          </Button>
        </form>

        <nav className="order-4 flex w-full flex-nowrap items-center gap-1 overflow-x-auto text-sm [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:order-none sm:w-auto sm:flex-wrap sm:overflow-visible">
          {NAV_ITEMS.map((item) => {
            const disabled = !username
            const to = username ? `/u/${username}${item.subpath}` : '/'
            return (
              <NavLink
                key={item.label}
                to={to}
                end={item.subpath === ''}
                aria-disabled={disabled}
                onClick={(event) => {
                  if (disabled) event.preventDefault()
                }}
                className={({ isActive }) =>
                  [
                    'flex min-h-11 shrink-0 items-center rounded-md px-3 py-1.5 transition',
                    disabled
                      ? 'cursor-not-allowed text-muted/50'
                      : isActive
                        ? 'bg-accent/15 text-accent-bright'
                        : 'text-muted hover:text-text',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            )
          })}
        </nav>

      </div>
    </header>
  )
}
