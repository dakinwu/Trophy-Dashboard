import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ApiError,
  getAdvisorLibrary,
  getAdvisorSignals,
  getGameDetail,
  getHltb,
  getProfile,
  getPlatinumGallery,
  getPsnprofilesGuide,
  getPsnprofilesStats,
  getPsnprofilesTrophies,
  type AdvisorBatchResponse,
  type AdvisorCandidate,
  type AdvisorLibrary,
  type GameTrophyDetail,
  type HltbTimes,
  type Platform,
  type ProfileData,
  type PlatinumGallery,
  type PsnprofilesGuide,
  type PsnprofilesStats,
  type PsnprofilesTrophyList,
} from './api'

/** Small independent gallery request; it never crawls the entire trophy log. */
export function usePlatinumGallery(username: string | undefined, enabled: boolean) {
  return useQuery<PlatinumGallery, ApiError>({
    queryKey: ['platinum-gallery', username],
    queryFn: () => getPlatinumGallery(username as string),
    enabled: Boolean(username) && enabled,
    retry: false,
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useAdvisorLibrary(username: string | undefined) {
  return useQuery<AdvisorLibrary, ApiError>({
    queryKey: ['advisor-library', username],
    queryFn: () => getAdvisorLibrary(username as string),
    enabled: Boolean(username),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRefreshAdvisorLibrary(username: string | undefined) {
  const queryClient = useQueryClient()
  const mutation = useMutation<AdvisorLibrary, ApiError>({
    mutationFn: () => getAdvisorLibrary(username as string, true),
    onSuccess: (data) => {
      queryClient.setQueryData(['advisor-library', username], data)
    },
  })
  return {
    refresh: mutation.mutate,
    refreshing: mutation.isPending,
    refreshError: mutation.error?.message ?? null,
  }
}

export function useAdvisorSignals() {
  return useMutation<AdvisorBatchResponse, ApiError, AdvisorCandidate[]>({
    mutationFn: (candidates) => getAdvisorSignals(candidates),
  })
}

export function useCachedAdvisorSignals(
  username: string | undefined,
  candidates: AdvisorCandidate[],
) {
  return useQuery<AdvisorBatchResponse, ApiError>({
    queryKey: [
      'advisor-signals-cache',
      username,
      candidates.map((candidate) => [candidate.game, candidate.platform]),
    ],
    queryFn: async () => {
      const results: AdvisorBatchResponse['results'] = []
      for (let start = 0; start < candidates.length; start += 50) {
        const response = await getAdvisorSignals(
          candidates.slice(start, start + 50),
          true,
        )
        results.push(...response.results)
      }
      return { results }
    },
    enabled: Boolean(username) && candidates.length > 0,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  })
}

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
          : '重新整理失敗，目前仍可使用原有的玩家資料。',
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
