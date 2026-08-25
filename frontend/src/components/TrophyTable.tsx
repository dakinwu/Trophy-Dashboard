import type { DataRow } from '../lib/dataTable'
import { formatTrophyRarity, GRADE_COLOR_VAR, GRADE_LABEL } from '../lib/trophy'

export function TrophyTable({ rows }: { rows: DataRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="rounded-2xl border border-border bg-surface p-6 text-center text-sm text-muted">
        沒有符合目前篩選條件的獎盃。
      </p>
    )
  }

  return (
    <div className="max-h-[70vh] overflow-auto rounded-2xl border border-border">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead className="sticky top-0 bg-surface">
          <tr className="text-left text-xs uppercase tracking-wide text-muted">
            <th className="px-3 py-2">遊戲</th>
            <th className="px-3 py-2">獎盃</th>
            <th className="px-3 py-2" title="依最近取得時間排序">
              取得時間 ↓
            </th>
            <th className="px-3 py-2">類型</th>
            <th className="px-3 py-2">稀有度</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={`${row.game}-${row.title}-${index}`}
              className="border-t border-border odd:bg-bg/20 hover:bg-bg/40"
            >
              <td className="max-w-[200px] truncate px-3 py-2 text-muted" title={row.game}>
                {row.game}
              </td>
              <td className="max-w-[260px] truncate px-3 py-2 text-text" title={row.title}>
                {row.title}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-muted">
                {row.parsedDate
                  ? row.parsedDate.toLocaleDateString('zh-TW', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })
                  : row.timestamp}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                <span
                  className="rounded-full border px-2 py-0.5 text-xs font-medium"
                  style={{
                    color: GRADE_COLOR_VAR[row.grade],
                    borderColor: GRADE_COLOR_VAR[row.grade],
                  }}
                >
                  {GRADE_LABEL[row.grade]}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-muted">
                {formatTrophyRarity(row)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
