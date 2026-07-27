import type { ChangeEvent } from 'react'
import type { TrophyGrade } from '../lib/api'
import { ALL_GRADES, type DataFilters } from '../lib/dataTable'
import { GRADE_COLOR_VAR } from '../lib/trophy'

interface TrophyFiltersProps {
  filters: DataFilters
  onChange: (filters: DataFilters) => void
}

/** Game search + grade multi-select + date-range controls for the Data page table. */
export function TrophyFilters({ filters, onChange }: TrophyFiltersProps) {
  function toggleGrade(grade: TrophyGrade) {
    const grades = new Set(filters.grades)
    if (grades.has(grade)) grades.delete(grade)
    else grades.add(grade)
    onChange({ ...filters, grades })
  }

  function handleSearch(event: ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, search: event.target.value })
  }

  function handleFrom(event: ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, from: event.target.value })
  }

  function handleTo(event: ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, to: event.target.value })
  }

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="game-search" className="text-xs uppercase tracking-wide text-muted">
          Game
        </label>
        <input
          id="game-search"
          value={filters.search}
          onChange={handleSearch}
          placeholder="Search games..."
          className="w-48 rounded-lg border border-border bg-bg px-3 py-1.5 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-muted">Grade</span>
        <div className="flex gap-1.5">
          {ALL_GRADES.map((grade) => {
            const active = filters.grades.has(grade)
            return (
              <button
                key={grade}
                type="button"
                onClick={() => toggleGrade(grade)}
                aria-pressed={active}
                className="rounded-full border px-2.5 py-1 text-xs font-medium transition"
                style={{
                  color: active ? GRADE_COLOR_VAR[grade] : 'var(--muted)',
                  borderColor: active ? GRADE_COLOR_VAR[grade] : 'var(--border)',
                  opacity: active ? 1 : 0.6,
                }}
              >
                {grade}
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="date-from" className="text-xs uppercase tracking-wide text-muted">
          From
        </label>
        <input
          id="date-from"
          type="date"
          value={filters.from}
          onChange={handleFrom}
          className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm text-text focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="date-to" className="text-xs uppercase tracking-wide text-muted">
          To
        </label>
        <input
          id="date-to"
          type="date"
          value={filters.to}
          onChange={handleTo}
          className="rounded-lg border border-border bg-bg px-3 py-1.5 text-sm text-text focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
    </div>
  )
}
