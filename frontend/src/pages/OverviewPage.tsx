import { useParams } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { OverviewHero } from '../components/overview/OverviewHero'
import { OverviewHeroSkeleton } from '../components/overview/OverviewHeroSkeleton'
import { PlatinumMosaic } from '../components/PlatinumMosaic'
import { PsnprofilesRankings } from '../components/PsnprofilesRankings'
import { RarestTrophies } from '../components/RarestTrophies'
import { ApiError } from '../lib/api'
import { useProfile, useRefreshProfile } from '../lib/queries'

export function OverviewPage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)
  const { refresh, refreshing, refreshError } = useRefreshProfile(username)

  if (!username) {
    return (
      <ErrorState
        title="No profile selected"
        message="Search for a PSN ID above to get started."
      />
    )
  }

  if (profileQuery.isLoading) {
    return <OverviewHeroSkeleton username={username} />
  }

  if (profileQuery.isError) {
    const error = profileQuery.error
    if (error instanceof ApiError && error.status === 404) {
      return (
        <ErrorState
          title="Profile not found"
          message={`We couldn't find "${username}" on PSNProfiles, or the profile is private.`}
        />
      )
    }
    if (error instanceof ApiError && error.status === 502) {
      return (
        <ErrorState
          title="Error fetching from PSNProfiles"
          message="PSNProfiles didn't respond correctly. Please try again in a moment."
        />
      )
    }
    return (
      <ErrorState
        title="Something went wrong"
        message={error instanceof Error ? error.message : 'Unknown error.'}
      />
    )
  }

  const data = profileQuery.data
  if (!data) {
    return <ErrorState title="No data" message="No profile data was returned." />
  }

  const { profile_summary, trophy_log } = data

  return (
    <div className="flex flex-col gap-6">
      <OverviewHero
        data={data}
        refreshing={refreshing}
        refreshError={refreshError}
        onRefresh={refresh}
      />
      <PsnprofilesRankings summary={profile_summary} />
      <div className="grid gap-6 lg:grid-cols-2">
        <PlatinumMosaic
          trophies={trophy_log}
          platinumGames={data.platinum_games}
          totalPlatinums={profile_summary.total_trophies.platinum}
        />
        <RarestTrophies trophies={trophy_log} />
      </div>
    </div>
  )
}
