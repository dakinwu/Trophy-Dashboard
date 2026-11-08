import type { PlatinumGame, Trophy } from '../lib/api'
import { ImageWithFallback } from './ImageWithFallback'
import { BorderBeam } from './magicui/BorderBeam'

interface PlatinumMosaicProps {
  trophies: Trophy[]
  platinumGames?: PlatinumGame[]
  totalPlatinums?: number
  loading?: boolean
  galleryError?: boolean
  onRetry?: () => void
  officialGallery?: boolean
}

export function PlatinumMosaic({
  trophies,
  platinumGames = [],
  totalPlatinums,
  loading = false,
  galleryError = false,
  onRetry,
  officialGallery = false,
}: PlatinumMosaicProps) {
  const platinums = trophies.filter((trophy) => trophy.grade === 'Platinum' && trophy.earned !== false)
  const usesGameSummaries = platinums.length === 0 && platinumGames.length > 0

  return (
    <section className="relative overflow-hidden rounded-2xl border border-border bg-surface p-5">
      <BorderBeam size={110} duration={13} delay={3} colorFrom="var(--platinum)" />
      <h2 className="mb-4 text-lg font-semibold text-text">
        {usesGameSummaries ? '白金遊戲' : '白金獎盃'}
      </h2>
      {officialGallery && <p className="mb-3 text-xs text-muted">圖片來源：Sony 官方原圖 · 本機快取</p>}
      {loading && <p role="status" className="mb-3 text-xs text-muted">正在核對完整白金清單，原圖會保存到本機…</p>}
      {galleryError && (
        <p className="mb-3 text-xs text-muted">
          暫時無法更新官方白金清單，目前顯示已取得的資料。
          <button type="button" onClick={onRetry} className="ml-2 rounded text-accent underline focus-visible:outline-2 focus-visible:outline-accent">重試</button>
        </p>
      )}
      {!usesGameSummaries && platinums.length > 0 && (
        <p className="mb-3 text-xs text-muted" aria-live="polite">
          已載入 {platinums.length.toLocaleString()}／{(totalPlatinums ?? platinums.length).toLocaleString()} 座白金獎盃。
          {totalPlatinums != null && platinums.length < totalPlatinums &&
            '部分獎盃明細尚未取得，請使用上方「重新整理資料」補齊。'}
        </p>
      )}
      {usesGameSummaries ? (
        <>
          <p className="mb-3 text-xs text-muted">
            顯示 {platinumGames.length.toLocaleString()} 款公開可見的白金遊戲
            {totalPlatinums ? `／共 ${totalPlatinums.toLocaleString()} 座白金` : ''}。
          </p>
          <div className="grid max-h-[32rem] grid-cols-2 gap-3 overflow-y-auto pr-1 sm:grid-cols-3">
            {platinumGames.map((game) => (
              <div
                key={`${game.game}-${game.platforms.join('-')}`}
                className="min-w-0 rounded-lg border border-border bg-bg/40 p-2"
                title={game.game}
              >
                <ImageWithFallback
                  src={game.icon_url}
                  alt=""
                  loading="lazy"
                  fallbackKind="game"
                  className="mb-2 aspect-square w-full rounded-md object-cover"
                />
                <p className="line-clamp-2 text-xs font-medium text-text">{game.game}</p>
              </div>
            ))}
          </div>
        </>
      ) : platinums.length === 0 ? (
        <p className="text-sm text-muted">目前尚未取得白金獎盃。</p>
      ) : (
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-6 md:grid-cols-8">
          {platinums.map((trophy, index) => (
            <ImageWithFallback
              key={`${trophy.game}-${trophy.title}-${index}`}
              src={trophy.icon_url}
              alt={trophy.title}
              title={trophy.game}
              loading="lazy"
              className="aspect-square w-full rounded-lg border border-border object-cover transition hover:-translate-y-0.5 hover:border-platinum"
            />
          ))}
        </div>
      )}
    </section>
  )
}
