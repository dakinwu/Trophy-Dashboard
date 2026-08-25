import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { ApiError, type ProfileData } from '../lib/api'
import { ErrorState } from './ErrorState'
import { LoadingProgress } from './LoadingProgress'

interface ProfileStateGateProps {
  username: string | undefined
  query: UseQueryResult<ProfileData, ApiError>
  children: (data: ProfileData) => ReactNode
}

/**
 * Shared no-username / loading / error / empty-data handling for every
 * `u/:username/*` page (mirrors OverviewPage's handling), so each page only
 * has to render its own happy path.
 */
export function ProfileStateGate({ username, query, children }: ProfileStateGateProps) {
  if (!username) {
    return (
      <ErrorState
        title="尚未選擇玩家"
        message="請先在上方搜尋 PSN ID。"
      />
    )
  }

  if (query.isLoading) {
    return <LoadingProgress username={username} />
  }

  if (query.isError) {
    const error = query.error
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

  if (!query.data) {
    return <ErrorState title="沒有資料" message="資料來源沒有回傳玩家資料。" />
  }

  return <>{children(query.data)}</>
}
