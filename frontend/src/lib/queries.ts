import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ApiError,
  getGameDetail,
  getHltb,
  getProfile,
  getPsnprofilesGuide,
  getPsnprofilesStats,
  getPsnprofilesTrophies,
  type GameTrophyDetail,
  type HltbTimes,
  type Platform,
  type ProfileData,
  type PsnprofilesGuide,
  type PsnprofilesStats,
  type PsnprofilesTrophyList,
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

export function useGameDetail(
  username: string | undefined,
  game: string | undefined,
) {
  return useQuery<GameTrophyDetail, ApiError>({
    queryKey: ['game-detail', username, game],
    queryFn: () => getGameDetail(username as string, game as string),
    enabled: Boolean(username && game),
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
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const refreshLock = useRef(false)

  useEffect(() => {
    setRefreshError(null)
  }, [username])

  async function refresh() {
    if (!username || refreshLock.current) return
    refreshLock.current = true
    setRefreshing(true)
    setRefreshError(null)
    try {
      const data = await getProfile(username, true)
      queryClient.setQueryData(['profile', username], data)
    } catch (error) {
      setRefreshError(
        error instanceof Error
          ? error.message
          : 'Refresh failed. The existing profile data is still available.',
      )
    } finally {
      refreshLock.current = false
      setRefreshing(false)
    }
  }

  return { refresh, refreshing, refreshError }
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

/** PSNProfiles rankings are opt-in because a cache miss opens visible Chrome. */
export function usePsnprofilesStats(username: string | undefined, enabled: boolean) {
  return useQuery<PsnprofilesStats | null>({
    queryKey: ['psnprofiles-stats', username],
    queryFn: () => getPsnprofilesStats(username as string),
    enabled: Boolean(username) && enabled,
    staleTime: 60 * 60 * 1000,
    retry: false,
  })
}

/** One title only, so PSNProfiles rarity enrichment is safe to load on entry. */
export function usePsnprofilesTrophies(
  game: string | undefined,
  platform: Platform | undefined,
) {
  return useQuery<PsnprofilesTrophyList | null>({
    queryKey: ['psnprofiles-trophies', game, platform],
    queryFn: () => getPsnprofilesTrophies(game as string, platform),
    enabled: Boolean(game),
    staleTime: 24 * 60 * 60 * 1000,
    retry: false,
  })
}
