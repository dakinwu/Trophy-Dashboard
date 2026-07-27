import type { TrophyCounts } from '../lib/api'

const TILES: { key: keyof TrophyCounts; label: string; colorVar: string }[] = [
  { key: 'total', label: 'Total', colorVar: 'var(--accent-bright)' },
  { key: 'platinum', label: 'Platinum', colorVar: 'var(--platinum)' },
  { key: 'gold', label: 'Gold', colorVar: 'var(--gold)' },
  { key: 'silver', label: 'Silver', colorVar: 'var(--silver)' },
  { key: 'bronze', label: 'Bronze', colorVar: 'var(--bronze)' },
]

/** Trophy-count tiles, plus a real playtime tile when available (PSN API source). */
export function StatTiles({ counts, playtime }: { counts: TrophyCounts; playtime?: string }) {
  const activeTile =
    'rounded-xl border border-border bg-surface p-4 text-center shadow-md shadow-black/10 transition hover:-translate-y-0.5 hover:shadow-lg'

  return (
    <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {TILES.map((tile) => (
        <div key={tile.key} className={activeTile}>
          <div className="text-2xl font-bold" style={{ color: tile.colorVar }}>
            {counts[tile.key].toLocaleString()}
          </div>
          <div className="mt-1 text-xs uppercase tracking-wide text-muted">{tile.label}</div>
        </div>
      ))}

      <div
        className={
          playtime
            ? activeTile
            : 'rounded-xl border border-dashed border-border bg-surface/50 p-4 text-center opacity-70'
        }
      >
        <div className={`text-2xl font-bold ${playtime ? 'text-accent' : 'text-muted'}`}>
          {playtime ?? '—'}
        </div>
        <div className="mt-1 text-xs uppercase tracking-wide text-muted">Playtime</div>
      </div>
    </section>
  )
}
