import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { TopGameSlice } from '../../lib/games'

const DONUT_COLORS = [
  'var(--accent)',
  'var(--platinum)',
  'var(--gold)',
  'var(--bronze)',
  'var(--silver)',
  'var(--accent-bright)',
  '#8b6dd6',
  '#4fae8c',
]

/** Donut chart of the top games by trophies earned, with a color-keyed legend list. */
export function TopGamesDonut({ data }: { data: TopGameSlice[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted">No games to chart yet.</p>
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div style={{ width: 200, height: 200 }} className="shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="total"
              nameKey="game"
              innerRadius="55%"
              outerRadius="90%"
              paddingAngle={2}
              stroke="var(--surface)"
              strokeWidth={2}
            >
              {data.map((entry, index) => (
                <Cell key={entry.game} fill={DONUT_COLORS[index % DONUT_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                color: 'var(--text)',
              }}
              labelStyle={{ color: 'var(--text)' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex min-w-0 flex-1 flex-col gap-1.5 text-sm">
        {data.map((entry, index) => (
          <li key={entry.game} className="flex min-w-0 items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: DONUT_COLORS[index % DONUT_COLORS.length] }}
            />
            <span className="truncate text-text">{entry.game}</span>
            <span className="ml-auto shrink-0 text-muted">{entry.total}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
