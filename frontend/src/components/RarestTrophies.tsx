import type { Trophy } from '../lib/api'
import { formatTrophyRarity, GRADE_COLOR_VAR, getRarestTrophies } from '../lib/trophy'

export function RarestTrophies({ trophies }: { trophies: Trophy[] }) {
  const rarest = getRarestTrophies(trophies, 5)

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="mb-4 text-lg font-semibold text-text">Rarest Trophies</h2>
      {rarest.length === 0 ? (
        <p className="text-sm text-muted">No trophy data available.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rarest.map((trophy, index) => (
            <li
              key={`${trophy.game}-${trophy.title}-${index}`}
              className="flex items-center gap-3 rounded-lg border border-border bg-bg/40 p-2 transition hover:-translate-y-0.5 hover:bg-bg/70"
            >
              <img
                src={trophy.icon_url}
                alt=""
                loading="lazy"
                className="h-10 w-10 shrink-0 rounded-md object-cover"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-text">{trophy.title}</p>
                <p className="truncate text-xs text-muted">{trophy.game}</p>
              </div>
              <span
                className="shrink-0 rounded-full border px-2 py-1 text-xs font-semibold"
                style={{
                  color: GRADE_COLOR_VAR[trophy.grade],
                  borderColor: GRADE_COLOR_VAR[trophy.grade],
                }}
              >
                {formatTrophyRarity(trophy)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
