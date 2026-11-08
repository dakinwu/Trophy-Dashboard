import { useParams } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { OverviewHero } from '../components/overview/OverviewHero'
import { OverviewHeroSkeleton } from '../components/overview/OverviewHeroSkeleton'
import { PlatinumMosaic } from '../components/PlatinumMosaic'
import { PsnprofilesRankings } from '../components/PsnprofilesRankings'
import { RarestTrophies } from '../components/RarestTrophies'
import { ApiError } from '../lib/api'
import { usePlatinumGallery, useProfile, useRefreshProfile } from '../lib/queries'

export function OverviewPage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)
  const galleryQuery = usePlatinumGallery(username, Boolean(profileQuery.data && !profileQuery.data.summary_only))
  const { refresh, refreshing, refreshError } = useRefreshProfile(username)

  if (!username) {
    return (
      <ErrorState
        title="尚未選擇玩家"
        message="請先在上方搜尋 PSN ID。"
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
          title="找不到玩家資料"
          message={`PSNProfiles 找不到「${username}」，或該玩家的個人資料未公開。`}
        />
      )
    }
    if (error instanceof ApiError && error.status === 502) {
      return (
        <ErrorState
          title="PSNProfiles 讀取失敗"
          message="PSNProfiles 沒有正確回應，請稍後再試。"
        />
      )
    }
    return (
      <ErrorState
        title="發生錯誤"
        message="目前無法載入玩家資料，請稍後再試。"
      />
    )
  }

  const data = profileQuery.data
  if (!data) {
    return <ErrorState title="沒有資料" message="資料來源沒有回傳玩家資料。" />
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
          trophies={galleryQuery.data?.trophies ?? (data.platinum_trophies?.length ? data.platinum_trophies : trophy_log)}
          platinumGames={data.platinum_games}
          totalPlatinums={galleryQuery.data?.total_count ?? profile_summary.total_trophies.platinum}
          loading={galleryQuery.isFetching}
          galleryError={galleryQuery.isError}
          officialGallery={Boolean(galleryQuery.data)}
          onRetry={() => void galleryQuery.refetch()}
        />
        <RarestTrophies trophies={trophy_log} />
      </div>
    </div>
  )
}
