import type { PlatinumGame, Trophy } from '../lib/api'
import { BorderBeam } from './magicui/BorderBeam'

interface PlatinumMosaicProps {
  trophies: Trophy[]
  platinumGames?: PlatinumGame[]
  totalPlatinums?: number
}

export function PlatinumMosaic({
  trophies,
  platinumGames = [],
  totalPlatinums,
}: PlatinumMosaicProps) {
  const platinums = trophies.filter((trophy) => trophy.grade === 'Platinum')
  const usesGameSummaries = platinums.length === 0 && platinumGames.length > 0

  return (
    <section className="relative overflow-hidden rounded-2xl border border-border bg-surface p-5">
      <BorderBeam size={110} duration={13} delay={3} colorFrom="var(--platinum)" />
      <h2 className="mb-4 text-lg font-semibold text-text">
        {usesGameSummaries ? 'Platinum Games' : 'Platinum Trophies'}
      </h2>
      {usesGameSummaries ? (
        <>
          <p className="mb-3 text-xs text-muted">
            Showing {platinumGames.length.toLocaleString()} publicly visible platinum games
            {totalPlatinums ? ` out of ${totalPlatinums.toLocaleString()} total platinums` : ''}.
          </p>
          <div className="grid max-h-[32rem] grid-cols-2 gap-3 overflow-y-auto pr-1 sm:grid-cols-3">
            {platinumGames.map((game) => (
              <div
                key={`${game.game}-${game.platforms.join('-')}`}
                className="min-w-0 rounded-lg border border-border bg-bg/40 p-2"
                title={game.game}
              >
                <img
                  src={game.icon_url}
                  alt=""
                  loading="lazy"
                  className="mb-2 aspect-square w-full rounded-md object-cover"
                />
                <p className="line-clamp-2 text-xs font-medium text-text">{game.game}</p>
              </div>
            ))}
          </div>
        </>
      ) : platinums.length === 0 ? (
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
