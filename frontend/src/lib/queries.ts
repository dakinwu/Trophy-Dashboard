import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ApiError,
  getHltb,
  getProfile,
  getPsnprofilesGuide,
  type HltbTimes,
  type ProfileData,
  type PsnprofilesGuide,
} from './api'

/**
 * Fetches a PSN profile + trophy log for `username` (served from the backend's
 * cache when fresh). Disabled until a username is present.
 */
export function useProfile(username: string | undefined) {
  return useQuery<ProfileData, ApiError>({
    queryKey: ['profile', username],
    queryFn: () => getProfile(username as string),
    enabled: Boolean(username),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Force-refresh a profile: re-fetch from source (bypassing the backend's 24h
 * cache) and replace the cached query data. Thanks to the per-title cache only
 * recently-played games are actually re-fetched upstream, so it's usually quick.
 */
export function useRefreshProfile(username: string | undefined) {
  const queryClient = useQueryClient()
  const [refreshing, setRefreshing] = useState(false)

  async function refresh() {
    if (!username || refreshing) return
    setRefreshing(true)
    try {
      const data = await getProfile(username, true)
      queryClient.setQueryData(['profile', username], data)
    } catch {
      // keep the existing data on failure
    } finally {
      setRefreshing(false)
    }
  }

  return { refresh, refreshing }
}

/** HowLongToBeat times for a game (long-cached, shared across cards). */
export function useHltb(game: string | undefined) {
  return useQuery<HltbTimes | null>({
    queryKey: ['hltb', game],
    queryFn: () => getHltb(game as string),
    enabled: Boolean(game),
    staleTime: 24 * 60 * 60 * 1000,
    retry: false,
  })
}

/**
 * PSNProfiles guide data is deliberately opt-in: a cache miss opens the visible
 * browser needed for Cloudflare, so mounting a page of cards must not trigger it.
 */
export function usePsnprofilesGuide(game: string | undefined, enabled: boolean) {
  return useQuery<PsnprofilesGuide | null>({
    queryKey: ['psnprofiles-guide', game],
    queryFn: () => getPsnprofilesGuide(game as string),
    enabled: Boolean(game) && enabled,
    staleTime: 24 * 60 * 60 * 1000,
    retry: false,
  })
}
