export interface GameLink {
  site: string
  label: string
  url: string
}

/**
 * Builds "search this game" links for external trophy/guide/info sites.
 *
 * These are SEARCH URLs built from the game name (no scraping, no game IDs),
 * so they work for any title without a backend fetch. PSNProfiles and
 * HowLongToBeat patterns are known-good; PSNine / Metacritic / Exophase use
 * best-known public search URLs — adjust a single line here if one lands on
 * the wrong page.
 */
export function buildGameLinks(game: string): GameLink[] {
  const q = encodeURIComponent(game)
  return [
    { site: 'psnprofiles', label: 'PSNProfiles', url: `https://psnprofiles.com/search/guides?q=${q}` },
    { site: 'psnine', label: 'PSNine', url: `https://psnine.com/psngame?key=${q}` },
    { site: 'hltb', label: 'HowLongToBeat', url: `https://howlongtobeat.com/?q=${q}` },
    { site: 'metacritic', label: 'Metacritic', url: `https://www.metacritic.com/search/${q}/` },
    { site: 'exophase', label: 'Exophase', url: `https://www.exophase.com/games/?q=${q}` },
  ]
}
