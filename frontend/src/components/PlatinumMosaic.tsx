import type { Trophy } from '../lib/api'

export function PlatinumMosaic({ trophies }: { trophies: Trophy[] }) {
  const platinums = trophies.filter((trophy) => trophy.grade === 'Platinum')

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="mb-4 text-lg font-semibold text-text">Platinum Trophies</h2>
      {platinums.length === 0 ? (
        <p className="text-sm text-muted">No platinum trophies yet.</p>
      ) : (
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 md:grid-cols-8">
          {platinums.map((trophy, index) => (
            <img
              key={`${trophy.game}-${trophy.title}-${index}`}
              src={trophy.icon_url}
              alt={trophy.title}
              title={trophy.game}
              loading="lazy"
              className="aspect-square w-full rounded-lg border border-border object-cover transition hover:-translate-y-0.5 hover:border-platinum"
            />
          ))}
        </div>
      )}
    </section>
  )
}
