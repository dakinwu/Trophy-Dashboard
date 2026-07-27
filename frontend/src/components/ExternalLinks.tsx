import { buildGameLinks } from '../lib/links'

/** A row of "search this game on <site>" links for external guide/info sites. */
export function ExternalLinks({
  game,
  psnprofilesGuideUrl,
}: {
  game: string
  psnprofilesGuideUrl?: string
}) {
  const links = buildGameLinks(game, psnprofilesGuideUrl)
  return (
    <div className="flex flex-wrap gap-1.5">
      {links.map((link) => (
        <a
          key={link.site}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`Search "${game}" on ${link.label}`}
          aria-label={`Search ${game} on ${link.label}`}
          className="rounded-full border border-border bg-bg/40 px-2 py-0.5 text-[11px] font-medium text-muted transition hover:border-accent hover:text-accent"
        >
          {link.label}
        </a>
      ))}
    </div>
  )
}
