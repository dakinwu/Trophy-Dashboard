export interface GameLink {
  site: string
  label: string
  url: string
}

/**
 * Builds "search this game" links for external trophy/guide/info sites.
 *
 * PSNine goes through a backend resolver so normal clicks, Ctrl-clicks, and
 * middle-clicks all land on its `?title=<Simplified Chinese name>` URL.
 */
export function buildGameLinks(game: string, psnprofilesGuideUrl?: string): GameLink[] {
  const q = encodeURIComponent(game)
  return [
    {
      site: 'psnprofiles',
      label: 'PSNProfiles',
      url: psnprofilesGuideUrl ?? `https://psnprofiles.com/search/guides?q=${q}`,
    },
    { site: 'psnine', label: 'PSNine', url: `/api/psnine?game=${q}` },
    { site: 'hltb', label: 'HowLongToBeat', url: `https://howlongtobeat.com/?q=${q}` },
    { site: 'metacritic', label: 'Metacritic', url: `https://www.metacritic.com/search/${q}/` },
    { site: 'exophase', label: 'Exophase', url: `https://www.exophase.com/games/?q=${q}` },
  ]
}
