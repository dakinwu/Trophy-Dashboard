import { Button, Input } from '@heroui/react'
import type { ChangeEvent } from 'react'
import type { TrophyGrade } from '../lib/api'
import { ALL_GRADES, type DataFilters } from '../lib/dataTable'
import { GRADE_COLOR_VAR, GRADE_LABEL } from '../lib/trophy'

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
          遊戲
        </label>
        <Input
          id="game-search"
          value={filters.search}
          onChange={handleSearch}
          placeholder="搜尋遊戲…"
          variant="secondary"
          className="w-48"
        />
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-muted">獎盃類型</span>
        <div className="flex gap-1.5">
          {ALL_GRADES.map((grade) => {
            const active = filters.grades.has(grade)
            return (
              <Button
                key={grade}
                type="button"
                onPress={() => toggleGrade(grade)}
                aria-pressed={active}
                size="sm"
                variant={active ? 'outline' : 'ghost'}
                className="min-w-0 px-2.5 text-xs"
                style={{
                  color: active ? GRADE_COLOR_VAR[grade] : 'var(--muted)',
                  borderColor: active ? GRADE_COLOR_VAR[grade] : 'var(--border)',
                  opacity: active ? 1 : 0.6,
                }}
              >
                {GRADE_LABEL[grade]}
              </Button>
            )
          })}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="date-from" className="text-xs uppercase tracking-wide text-muted">
          開始日期
        </label>
        <Input
          id="date-from"
          type="date"
          value={filters.from}
          onChange={handleFrom}
          variant="secondary"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="date-to" className="text-xs uppercase tracking-wide text-muted">
          結束日期
        </label>
        <Input
          id="date-to"
          type="date"
          value={filters.to}
          onChange={handleTo}
          variant="secondary"
        />
      </div>
    </div>
  )
}
