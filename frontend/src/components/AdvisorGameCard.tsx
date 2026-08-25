import { Button } from '@heroui/react'
import type { AdvisorBundleResult, AdvisorGame, PsnprofilesAdvisorSignals } from '../lib/api'
import { advisorScore, type AdvisorWeights } from '../lib/advisor'
import { formatPlaytime } from '../lib/games'
import { MagicCard } from './magicui/MagicCard'
import { PlatformLogos } from './PlatformLogos'

const STATUS_LABEL = {
  unplayed: '尚未遊玩',
  in_progress: '進行中',
  completed: '已完成',
} as const

const STATUS_CLASS = {
  unplayed: 'border-platinum/35 bg-platinum/10 text-platinum',
  in_progress: 'border-accent/35 bg-accent/10 text-accent-bright',
  completed: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-300',
} as const

const AUTOPOP_LABEL = {
  full: 'PS4→PS5 完整自動跳杯',
  partial: 'PS4→PS5 部分自動跳杯',
  none: 'PS4→PS5 不支援繼承',
  unknown: 'PS4→PS5 尚待確認',
} as const

const AUTOPOP_CLASS = {
  full: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-200',
  partial: 'border-accent/35 bg-accent/10 text-accent-bright',
  none: 'border-red-300/25 bg-red-300/5 text-red-200',
  unknown: 'border-platinum/25 bg-platinum/5 text-platinum',
} as const

function formatPercent(value: number | null): string {
  return value == null ? '無法取得' : `${value.toFixed(1)}%`
}

function SignalMetrics({ signals }: { signals: PsnprofilesAdvisorSignals }) {
  return (
    <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
      <div>
        <dt className="text-muted">追蹤玩家數</dt>
        <dd className="font-semibold tabular-nums text-text">{signals.owners?.toLocaleString() ?? '無法取得'}</dd>
      </div>
      <div>
        <dt className="text-muted">平均獎盃完成率</dt>
        <dd className="font-semibold tabular-nums text-text">{formatPercent(signals.average_completion)}</dd>
      </div>
      <div>
        <dt className="text-muted">白金率</dt>
        <dd className="font-semibold tabular-nums text-text">{formatPercent(signals.platinum_rate)}</dd>
      </div>
      <div>
        <dt className="text-muted">白金玩家數</dt>
        <dd className="font-semibold tabular-nums text-text">{signals.platinum_achievers?.toLocaleString() ?? '無法取得'}</dd>
      </div>
    </dl>
  )
}

export function AdvisorGameCard({
  game,
  signals,
  bundle,
  weights,
  maxPlatinumAchievers,
  analyzing,
  analysisDisabled,
  analysisError,
  onAnalyze,
}: {
  game: AdvisorGame
  signals?: PsnprofilesAdvisorSignals
  bundle?: AdvisorBundleResult
  weights: AdvisorWeights
  maxPlatinumAchievers: number
  analyzing: boolean
  analysisDisabled: boolean
  analysisError?: string
  onAnalyze: () => void
}) {
  const childScores = (bundle?.children ?? [])
    .map((child) => advisorScore(child.signals ?? undefined, maxPlatinumAchievers, weights))
    .filter((value): value is number => value != null)
  const score = advisorScore(signals, maxPlatinumAchievers, weights)
    ?? (childScores.length > 0 ? Math.max(...childScores) : null)
  const displayTitle = signals?.title || game.name
  const showsAutopop =
    game.ps4_to_ps5_autopop != null &&
    game.available_platforms.includes('PS4') &&
    game.available_platforms.includes('PS5')
  return (
    <MagicCard className="h-full rounded-2xl transition duration-300 hover:-translate-y-1 hover:shadow-[0_18px_45px_rgba(0,0,0,0.3)]">
      <article className="flex h-full min-h-[25rem] flex-col overflow-hidden">
        <div className="relative border-b border-border/70 p-4">
          {game.image_url && (
            <div
              aria-hidden="true"
              className="absolute inset-0 scale-125 bg-cover bg-center opacity-20 blur-2xl"
              style={{ backgroundImage: `url(${JSON.stringify(game.image_url).slice(1, -1)})` }}
            />
          )}
          <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-br from-surface/55 via-surface/90 to-bg" />
          <div className="relative flex items-start gap-3">
            {game.image_url ? (
              <img
                src={game.image_url}
                alt=""
                loading="lazy"
                className="h-20 w-20 shrink-0 rounded-xl border border-white/15 object-cover shadow-xl shadow-black/30"
              />
            ) : (
              <div aria-hidden="true" className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl border border-border bg-bg text-xl font-black text-accent">
                PS
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h2 className="line-clamp-3 text-sm font-bold leading-5 text-text" title={displayTitle}>
                {displayTitle}
              </h2>
              {displayTitle.toLocaleLowerCase() !== game.name.toLocaleLowerCase() && (
                <p className="mt-1 line-clamp-2 text-[10px] leading-4 text-muted" title={game.name}>
                  Sony 收藏庫：{game.name}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <PlatformLogos platforms={game.available_platforms.length > 0 ? game.available_platforms : [game.platform]} />
                {game.available_platforms.length > 1 && (
                  <span className="rounded-md border border-border bg-bg/45 px-2 py-1 text-[10px] font-semibold text-muted">
                    建議版本 {game.platform}
                  </span>
                )}
                <span className={`rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${STATUS_CLASS[game.status]}`}>
                  {STATUS_LABEL[game.status]}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-1 flex-col p-4">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-border/70 bg-bg/35 p-2.5">
              <p className="text-[10px] uppercase tracking-wide text-muted">我的進度</p>
              <p className="mt-1 font-semibold tabular-nums text-text">
                {game.progress == null ? '沒有獎盃資料' : `${game.progress}%`}
              </p>
            </div>
            <div className="rounded-lg border border-border/70 bg-bg/35 p-2.5">
              <p className="text-[10px] uppercase tracking-wide text-muted">遊玩時間</p>
              <p className="mt-1 font-semibold text-text">
                {game.playtime_seconds == null ? '無法取得' : formatPlaytime(game.playtime_seconds)}
              </p>
            </div>
          </div>

          {showsAutopop && game.ps4_to_ps5_autopop && (
            <div
              className={`mt-3 rounded-xl border p-3 ${AUTOPOP_CLASS[game.ps4_to_ps5_autopop]}`}
              aria-label={`獎盃繼承狀態：${AUTOPOP_LABEL[game.ps4_to_ps5_autopop]}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-bold">
                  {AUTOPOP_LABEL[game.ps4_to_ps5_autopop]}
                </p>
                {game.ps4_platinum_earned && (
                  <span className="rounded-full border border-current/30 px-2 py-0.5 text-[10px] font-bold">
                    PS4 已白金
                  </span>
                )}
              </div>
              {game.autopop_note && (
                <p className="mt-1.5 text-[11px] leading-5 text-current/80">
                  {game.autopop_note}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-current/65">
                {game.autopop_verified_at && (
                  <span>查證日期：{game.autopop_verified_at}</span>
                )}
                {game.autopop_source_url && (
                  <a
                    href={game.autopop_source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-bold underline decoration-current/40 underline-offset-2 hover:text-current"
                  >
                    查證來源
                  </a>
                )}
              </div>
            </div>
          )}

          <div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent">
                {bundle ? `合集內含 ${bundle.children.length} 套獎盃` : 'PSNProfiles 指標'}
              </p>
              {score != null && (
                <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs font-bold tabular-nums text-accent-bright">
                  推薦分數 {score.toFixed(0)}
                </span>
              )}
            </div>
            {bundle ? (
              <div className="mt-3 space-y-2">
                {bundle.children.map((child) => {
                  const childScore = advisorScore(child.signals ?? undefined, maxPlatinumAchievers, weights)
                  return (
                    <div key={`${child.game}-${child.platform ?? 'UNKNOWN'}`} className="rounded-lg border border-border/70 bg-bg/35 p-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-xs font-bold leading-5 text-text">{child.game}</p>
                          <p className="text-[10px] text-muted">{child.platform ?? '平台不明'}</p>
                        </div>
                        {childScore != null && (
                          <span className="shrink-0 rounded-full bg-accent/15 px-2 py-0.5 text-[10px] font-bold tabular-nums text-accent-bright">
                            {childScore.toFixed(0)} 分
                          </span>
                        )}
                      </div>
                      {child.signals ? (
                        <>
                          <SignalMetrics signals={child.signals} />
                          <a
                            href={child.signals.game_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 inline-flex text-[10px] font-bold text-accent underline decoration-accent/40 underline-offset-2"
                          >
                            開啟這套 PSNProfiles 獎盃列表
                          </a>
                        </>
                      ) : (
                        <p className="mt-2 text-[10px] text-muted">{child.error ?? '尚未取得 PSNProfiles 指標'}</p>
                      )}
                    </div>
                  )
                })}
                <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted">
                  <span>
                    {bundle.source === 'gemini_grounding' ? 'Gemini 2.5 Flash · Google Search' : '專案內建合集資料'}
                    {' · '}{bundle.verified_at}
                  </span>
                  {bundle.source_urls[0] && (
                    <a href={bundle.source_urls[0]} target="_blank" rel="noreferrer" className="font-bold text-accent underline underline-offset-2">
                      查找來源
                    </a>
                  )}
                </div>
              </div>
            ) : signals ? (
              <SignalMetrics signals={signals} />
            ) : (
              <p className="mt-2 text-xs leading-5 text-muted">
                分析這款遊戲以取得 PSNProfiles 的白金率與白金玩家數。
              </p>
            )}
            {analysisError && <p className="mt-2 text-xs text-red-300">{analysisError}</p>}
          </div>

          <div className="mt-auto pt-4">
            {signals ? (
              <a
                href={signals.game_url}
                target="_blank"
                rel="noreferrer"
                className="flex min-h-11 items-center justify-center rounded-lg border border-accent/35 bg-accent/10 px-3 py-2 text-xs font-bold text-accent transition hover:border-accent hover:bg-accent/15"
              >
                開啟 PSNProfiles 獎盃列表
              </a>
            ) : bundle?.complete ? null : (
              <Button type="button" onPress={onAnalyze} isPending={analyzing} isDisabled={analysisDisabled} variant="outline" className="min-h-11 w-full">
                使用 PSNProfiles 分析
              </Button>
            )}
            <div className="mt-3 flex items-center justify-between text-[10px] uppercase tracking-wide text-muted">
              <span>{game.source === 'ps_plus' ? 'PlayStation Plus' : game.source === 'purchased' ? '自行購買' : '其他授權'}</span>
              <span>{game.is_downloadable ? '可下載' : '目前無法下載'}</span>
            </div>
          </div>
        </div>
      </article>
    </MagicCard>
  )
}
