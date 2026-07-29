import playstationLogo from 'simple-icons/icons/playstation.svg'
import playstation3Logo from 'simple-icons/icons/playstation3.svg'
import playstation4Logo from 'simple-icons/icons/playstation4.svg'
import playstation5Logo from 'simple-icons/icons/playstation5.svg'
import playstationVitaLogo from 'simple-icons/icons/playstationvita.svg'
import type { Platform } from '../lib/api'

const PLATFORM_META: Record<Platform, { label: string; logo: string }> = {
  PS3: { label: 'PlayStation 3', logo: playstation3Logo },
  PS4: { label: 'PlayStation 4', logo: playstation4Logo },
  PS5: { label: 'PlayStation 5', logo: playstation5Logo },
  PSVITA: { label: 'PlayStation Vita', logo: playstationVitaLogo },
  PSPC: { label: 'PlayStation PC', logo: playstationLogo },
  UNKNOWN: { label: 'PlayStation platform unknown', logo: playstationLogo },
}

export function PlatformLogos({ platforms }: { platforms: Platform[] }) {
  const sourcePlatforms: Platform[] = platforms.length > 0 ? platforms : ['UNKNOWN']
  const uniquePlatforms = [...new Set<Platform>(sourcePlatforms)]

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1" aria-label="Platforms">
      {uniquePlatforms.map((platform) => {
        const meta = PLATFORM_META[platform]
        return (
          <span
            key={platform}
            title={meta.label}
            aria-label={meta.label}
            className="flex h-6 min-w-10 items-center justify-center rounded-md border border-border bg-text px-1.5"
          >
            <img
              src={meta.logo}
              alt={meta.label}
              className="h-4 w-10 object-contain"
            />
          </span>
        )
      })}
    </div>
  )
}
