import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MonthlyGradeCounts } from '../../lib/timeline'
import { GRADE_LABEL } from '../../lib/trophy'

const BARS: { key: 'Bronze' | 'Silver' | 'Gold' | 'Platinum'; color: string }[] = [
  { key: 'Bronze', color: 'var(--bronze)' },
  { key: 'Silver', color: 'var(--silver)' },
  { key: 'Gold', color: 'var(--gold)' },
  { key: 'Platinum', color: 'var(--platinum)' },
]

/** Monthly trophies-earned bar chart, stacked bottom-to-top: Bronze, Silver, Gold, Platinum. */
export function MonthlyTrophyChart({ data }: { data: MonthlyGradeCounts[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted">目前沒有可繪製的獎盃日期資料。</p>
  }

  const width = Math.max(600, data.length * 44)

  return (
    <div className="overflow-x-auto">
      <div style={{ width, height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="monthLabel"
              tick={{ fill: 'var(--muted)', fontSize: 12 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: 'var(--muted)', fontSize: 12 }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: 'var(--border)', opacity: 0.3 }}
              contentStyle={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                color: 'var(--text)',
              }}
              labelStyle={{ color: 'var(--text)' }}
            />
            <Legend wrapperStyle={{ color: 'var(--muted)', fontSize: 12 }} />
            {BARS.map((bar) => (
              <Bar key={bar.key} dataKey={bar.key} name={GRADE_LABEL[bar.key]} stackId="grade" fill={bar.color} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
