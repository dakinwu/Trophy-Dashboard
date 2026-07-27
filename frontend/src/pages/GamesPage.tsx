import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { FastestPlatinumsChart } from '../components/charts/FastestPlatinumsChart'
import { RarityDistributionChart } from '../components/charts/RarityDistributionChart'
import { TopGamesDonut } from '../components/charts/TopGamesDonut'
import { ErrorState } from '../components/ErrorState'
import { GameCard } from '../components/GameCard'
import { ProfileStateGate } from '../components/ProfileStateGate'
import type { Trophy } from '../lib/api'
import { getRarityDistribution, getTopGamesByTrophies, groupTrophiesByGame } from '../lib/games'
import { useProfile } from '../lib/queries'
import { getFastestPlatinumsByGame } from '../lib/trophy'

export function GamesPage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)

  return (
    <ProfileStateGate username={username} query={profileQuery}>
      {(data) => (
        <GamesContent trophyLog={data.trophy_log} playtime={data.game_playtime_seconds} />
      )}
    </ProfileStateGate>
  )
}

function GamesContent({
  trophyLog,
  playtime,
}: {
  trophyLog: Trophy[]
  playtime?: Record<string, number>
}) {
  const summaries = useMemo(() => groupTrophiesByGame(trophyLog, playtime), [trophyLog, playtime])
  const sortedByRecent = useMemo(
    () =>
      [...summaries].sort(
        (a, b) => (b.lastEarnedDate?.getTime() ?? -1) - (a.lastEarnedDate?.getTime() ?? -1),
      ),
    [summaries],
  )
  const rarityDistribution = useMemo(() => getRarityDistribution(trophyLog), [trophyLog])
  const raritySource = trophyLog.find((trophy) => trophy.rarity_source)?.rarity_source
  const raritySourceLabel =
    raritySource === 'psn' ? 'PSN' : raritySource === 'psnprofiles' ? 'PSNProfiles' : null
  const topGames = useMemo(() => getTopGamesByTrophies(summaries, 8), [summaries])
  const fastestPlatinums = useMemo(
    () => getFastestPlatinumsByGame(trophyLog).slice(0, 8),
    [trophyLog],
  )

  if (summaries.length === 0) {
    return <ErrorState title="No games yet" message="This profile has no logged trophies." />
  }

  return (
    <div className="flex flex-col gap-6">
      <section>
        <h1 className="mb-4 text-lg font-semibold text-text">Games</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sortedByRecent.map((summary) => (
            <GameCard key={summary.game} summary={summary} />
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text">Insights</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h3 className="mb-4 text-sm font-semibold text-text">
              Rarity Distribution
              {raritySourceLabel && (
                <span className="ml-1 font-normal text-muted">· {raritySourceLabel}</span>
              )}
            </h3>
            <RarityDistributionChart data={rarityDistribution} />
          </div>
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h3 className="mb-4 text-sm font-semibold text-text">Top Games by Trophies</h3>
            <TopGamesDonut data={topGames} />
          </div>
          <div className="rounded-2xl border border-border bg-surface p-5 lg:col-span-2">
            <h3 className="mb-4 text-sm font-semibold text-text">Fastest Platinums</h3>
            <FastestPlatinumsChart data={fastestPlatinums} />
          </div>
        </div>
      </section>
    </div>
  )
}
