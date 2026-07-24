import { useQuery } from '@tanstack/react-query'
import { ApiError, getHltb, getProfile, type HltbTimes, type ProfileData } from './api'

/**
 * Fetches a PSN profile + trophy log for `username`.
 * Disabled until a username is present so pages can call it unconditionally.
 */
export function useProfile(username: string | undefined, refresh = false) {
  return useQuery<ProfileData, ApiError>({
    queryKey: ['profile', username, refresh],
    queryFn: () => getProfile(username as string, refresh),
    enabled: Boolean(username),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
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
