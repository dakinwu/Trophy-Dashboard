import playstationLogo from 'simple-icons/icons/playstation.svg'
import playstation3Logo from 'simple-icons/icons/playstation3.svg'
import playstation4Logo from 'simple-icons/icons/playstation4.svg'
import playstation5Logo from 'simple-icons/icons/playstation5.svg'
import playstationVitaLogo from 'simple-icons/icons/playstationvita.svg'
import type { Platform } from '../lib/api'

interface PlatformMeta {
  label: string
  logo: string
  badgeClass: string
  logoClass: string
}

const PLATFORM_META: Record<Platform, PlatformMeta> = {
  PS3: {
    label: 'PlayStation 3',
    logo: playstation3Logo,
    badgeClass: 'border-white/20 bg-black',
    logoClass: 'brightness-0 invert',
  },
  PS4: {
    label: 'PlayStation 4',
    logo: playstation4Logo,
    badgeClass: 'border-[#1681d8] bg-[#006fcd]',
    logoClass: 'brightness-0 invert',
  },
  PS5: {
    label: 'PlayStation 5',
    logo: playstation5Logo,
    badgeClass: 'border-white/80 bg-white',
    logoClass: 'brightness-0',
  },
  PSVITA: {
    label: 'PlayStation Vita',
    logo: playstationVitaLogo,
    badgeClass: 'border-[#2456a6] bg-[#003791]',
    logoClass: 'brightness-0 invert',
  },
  PSPC: {
    label: 'PlayStation PC',
    logo: playstationLogo,
    badgeClass: 'border-white/30 bg-slate-800',
    logoClass: 'brightness-0 invert',
  },
  UNKNOWN: {
    label: '未知的 PlayStation 平台',
    logo: playstationLogo,
    badgeClass: 'border-white/20 bg-slate-700',
    logoClass: 'brightness-0 invert',
  },
}

export function PlatformLogos({ platforms }: { platforms: Platform[] }) {
  const sourcePlatforms: Platform[] = platforms.length > 0 ? platforms : ['UNKNOWN']
  const uniquePlatforms = [...new Set<Platform>(sourcePlatforms)]

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1" aria-label="平台">
      {uniquePlatforms.map((platform) => {
        const meta = PLATFORM_META[platform]
        return (
          <span
            key={platform}
            title={meta.label}
            aria-label={meta.label}
            className={`flex h-7 min-w-11 items-center justify-center rounded-md border px-1 shadow-sm ${meta.badgeClass}`}
          >
            <img
              src={meta.logo}
              alt={meta.label}
              className={`h-6 w-11 object-contain ${meta.logoClass}`}
            />
          </span>
        )
      })}
    </div>
  )
}
