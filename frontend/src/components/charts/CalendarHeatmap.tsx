import { useEffect, useMemo, useState } from 'react'
import { getActivityYears, getHeatmapLevel } from '../../lib/timeline'
import { toDateKey } from '../../lib/trophy'

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const LEVEL_ACCENT_PERCENT = [0, 28, 52, 74, 100]

interface DayCell {
  key: string
  count: number
  inYear: boolean
}

function buildYearWeeks(year: number, dailyActivity: Map<string, number>): DayCell[][] {
  const dec31 = new Date(year, 11, 31)
  const cursor = new Date(year, 0, 1)
  cursor.setDate(cursor.getDate() - cursor.getDay()) // back up to the preceding Sunday

  const weeks: DayCell[][] = []
  while (cursor <= dec31) {
    const week: DayCell[] = []
    for (let i = 0; i < 7; i++) {
      const key = toDateKey(cursor)
      week.push({ key, count: dailyActivity.get(key) ?? 0, inYear: cursor.getFullYear() === year })
      cursor.setDate(cursor.getDate() + 1)
    }
    weeks.push(week)
  }
  return weeks
}

/** Hand-rolled GitHub-style contribution grid for a single year, colored by daily trophy count. */
export function CalendarHeatmap({ dailyActivity }: { dailyActivity: Map<string, number> }) {
  const years = useMemo(() => getActivityYears(dailyActivity), [dailyActivity])
  const [year, setYear] = useState<number | null>(years[0] ?? null)

  useEffect(() => {
    setYear(years[0] ?? null)
  }, [years])

  const selectedYear = year !== null && years.includes(year) ? year : (years[0] ?? null)

  const weeks = useMemo(
    () => (selectedYear !== null ? buildYearWeeks(selectedYear, dailyActivity) : []),
    [selectedYear, dailyActivity],
  )

  const maxCount = useMemo(() => {
    let max = 0
    for (const week of weeks) {
      for (const day of week) {
        if (day.inYear) max = Math.max(max, day.count)
      }
    }
    return max
  }, [weeks])

  if (selectedYear === null) {
    return <p className="text-sm text-muted">No dated trophies to chart yet.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {years.length > 1 && (
        <div className="flex flex-wrap gap-1">
          {years.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setYear(y)}
              className={[
                'rounded-md px-2.5 py-1 text-xs font-medium transition',
                y === selectedYear ? 'bg-accent text-bg' : 'bg-bg/40 text-muted hover:text-text',
              ].join(' ')}
            >
              {y}
            </button>
          ))}
        </div>
      )}

      <div className="overflow-x-auto pb-1">
        <div className="flex w-max gap-[3px]">
          <div className="flex flex-col gap-[3px] pr-1 text-[10px] text-muted">
            {WEEKDAY_LABELS.map((label, index) => (
              <span key={label} className="h-[11px] leading-[11px]">
                {index % 2 === 1 ? label.slice(0, 3) : ''}
              </span>
            ))}
          </div>
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="flex flex-col gap-[3px]">
              {week.map((day) => {
                const level = day.inYear ? getHeatmapLevel(day.count, maxCount) : 0
                return (
                  <div
                    key={day.key}
                    title={day.inYear ? `${day.key}: ${day.count} trophies` : undefined}
                    className="h-[11px] w-[11px] rounded-[2px]"
                    style={{
                      backgroundColor: !day.inYear
                        ? 'transparent'
                        : level === 0
                          ? 'var(--surface)'
                          : `color-mix(in srgb, var(--accent) ${LEVEL_ACCENT_PERCENT[level]}%, var(--surface))`,
                      border: day.inYear ? '1px solid var(--border)' : 'none',
                    }}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-1 self-end text-[11px] text-muted">
        <span>Less</span>
        {LEVEL_ACCENT_PERCENT.map((percent, index) => (
          <span
            key={index}
            className="h-[11px] w-[11px] rounded-[2px] border border-border"
            style={{
              backgroundColor:
                percent === 0
                  ? 'var(--surface)'
                  : `color-mix(in srgb, var(--accent) ${percent}%, var(--surface))`,
            }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
