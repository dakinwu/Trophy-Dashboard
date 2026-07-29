import { Button, Input } from '@heroui/react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, useMatch, useNavigate } from 'react-router-dom'
import { useRefreshProfile } from '../lib/queries'

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
  const { refresh, refreshing } = useRefreshProfile(username)

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

        <form onSubmit={handleSubmit} className="flex min-w-[200px] flex-1 items-center gap-2">
          <Input
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

        <nav className="flex flex-wrap items-center gap-1 text-sm">
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
                    'rounded-md px-3 py-1.5 transition',
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

        {username && (
          <Button
            type="button"
            onPress={refresh}
            isDisabled={refreshing}
            isPending={refreshing}
            size="sm"
            variant="outline"
            aria-label="Refresh trophies from PSN and bypass the cache"
            className="shrink-0"
          >
            {refreshing ? 'Refreshing…' : '🔄 Refresh'}
          </Button>
        )}
      </div>
    </header>
  )
}
