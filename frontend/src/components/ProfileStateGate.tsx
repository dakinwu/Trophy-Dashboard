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
        title="No profile selected"
        message="Search for a PSN ID above to get started."
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

  if (!query.data) {
    return <ErrorState title="No data" message="No profile data was returned." />
  }

  return <>{children(query.data)}</>
}
