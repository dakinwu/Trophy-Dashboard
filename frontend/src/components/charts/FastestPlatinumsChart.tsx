import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatDuration, type FastestPlatinumResult } from '../../lib/trophy'

interface DurationTooltipProps {
  active?: boolean
  payload?: { payload: { game: string; label: string } }[]
}

function DurationTooltip({ active, payload }: DurationTooltipProps) {
  if (!active || !payload || payload.length === 0) return null
  const { game, label } = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      <div className="font-medium text-text">{game}</div>
      <div className="text-muted">{label}</div>
    </div>
  )
}

/** Horizontal bar chart of the fastest game-first-trophy -> platinum completions. */
export function FastestPlatinumsChart({ data }: { data: FastestPlatinumResult[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted">目前尚未取得白金獎盃。</p>
  }

  const chartData = data.map((entry) => ({
    game: entry.game,
    hours: Math.max(entry.durationMs / 3_600_000, 0.01),
    label: formatDuration(entry.durationMs),
  }))

  const height = Math.max(180, chartData.length * 34)

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
            allowDecimals={false}
            label={{
              value: '小時',
              position: 'insideBottom',
              offset: -2,
              fill: 'var(--muted)',
              fontSize: 11,
            }}
          />
          <YAxis
            type="category"
            dataKey="game"
            width={140}
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border)' }}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: 'var(--border)', opacity: 0.3 }}
            content={<DurationTooltip />}
          />
          <Bar dataKey="hours" fill="var(--platinum)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
