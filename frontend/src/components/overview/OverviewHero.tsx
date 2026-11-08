import { Avatar, Button, Tabs } from '@heroui/react'
import { motion, useReducedMotion } from 'motion/react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ProfileData } from '../../lib/api'
import {
  buildOverviewHeroViewModel,
  type HeroMetricTone,
  type OverviewHeroViewModel,
} from '../../lib/overviewHero'
import { GRADE_COLOR_VAR, GRADE_LABEL, rarityForSource } from '../../lib/trophy'
import { BorderBeam } from '../magicui/BorderBeam'
import { ImageWithFallback } from '../ImageWithFallback'
import { NumberTicker } from '../magicui/NumberTicker'
import { TrophyLevelGauge } from './TrophyLevelGauge'
import { useHeroSpotlight } from './useHeroSpotlight'

interface OverviewHeroProps {
  data: ProfileData
  refreshing: boolean
  refreshError: string | null
  onRefresh: () => Promise<void>
}

type HeroTabKey = 'progress' | 'rarity' | 'recent'

const TONE_CLASS: Record<HeroMetricTone, string> = {
  accent: 'text-accent-bright',
  platinum: 'text-platinum',
  text: 'text-text',
  muted: 'text-muted',
}

function formatUpdatedAt(value: Date | null): string | null {
  if (!value) return null
  return new Intl.DateTimeFormat('zh-TW', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(value)
}

function PanelTransition({ children }: { children: React.ReactNode }) {
  const prefersReducedMotion = useReducedMotion()
  return (
    <motion.div
      initial={prefersReducedMotion ? false : { opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

function ProgressPanel({ viewModel }: { viewModel: OverviewHeroViewModel }) {
  const gameProgress =
    viewModel.completionPercent ??
    (viewModel.gamesPlayed !== null &&
    viewModel.gamesPlayed > 0 &&
    viewModel.completedGames !== null
      ? (viewModel.completedGames / viewModel.gamesPlayed) * 100
      : null)
  const normalizedProgress =
    gameProgress === null ? null : Math.min(100, Math.max(0, gameProgress))

  return (
    <PanelTransition>
      <div className="min-h-56">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
              遊戲進度
            </p>
            {viewModel.completedGames !== null && viewModel.gamesPlayed !== null ? (
              <p className="mt-1 text-lg font-bold text-text">
                {viewModel.completedGames.toLocaleString()}
                <span className="font-normal text-muted">
                  {' '}
                  ／共 {viewModel.gamesPlayed.toLocaleString()} 款已完成
                </span>
              </p>
            ) : viewModel.completionPercent !== null ? (
              <p className="mt-1 text-lg font-bold text-text">
                {viewModel.completionPercent}% <span className="font-normal text-muted">完成率</span>
              </p>
            ) : (
              <p className="mt-1 text-sm text-muted">無法取得遊戲完成資料。</p>
            )}
          </div>
          {normalizedProgress !== null && (
            <span className="shrink-0 text-sm font-bold tabular-nums text-accent">
              {Math.round(normalizedProgress)}%
            </span>
          )}
        </div>

        {normalizedProgress !== null && (
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-border/60"
            role="progressbar"
            aria-label="遊戲完成進度"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(normalizedProgress)}
          >
            <div
              className="h-full origin-left rounded-full bg-accent transition-transform duration-500 motion-reduce:transition-none"
              style={{ transform: `scaleX(${normalizedProgress / 100})` }}
            />
          </div>
        )}

        <div className="mt-6 flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
              獎盃收藏
            </p>
            <p className="mt-1 text-sm text-muted">
              共 {viewModel.totalTrophies.toLocaleString()} 座獎盃
            </p>
          </div>
        </div>

        <div
          className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-border/50"
          role="img"
          aria-label={viewModel.trophyMix
            .map((item) => `${item.grade}: ${item.count}`)
            .join(', ')}
        >
          {viewModel.trophyMix.map((item) =>
            item.count > 0 ? (
              <span
                key={item.grade}
                className="h-full min-w-1"
                style={{
                  backgroundColor: GRADE_COLOR_VAR[item.grade],
                  flexGrow: item.count,
                }}
              />
            ) : null,
          )}
        </div>
        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {viewModel.trophyMix.map((item) => (
            <div key={item.grade} className="min-w-0 rounded-lg border border-border/70 bg-bg/35 p-2 text-center">
              <p
                className="truncate text-[10px] font-black uppercase"
                title={GRADE_LABEL[item.grade]}
                style={{ color: GRADE_COLOR_VAR[item.grade] }}
              >
                {GRADE_LABEL[item.grade]}
              </p>
              <p className="mt-1 truncate text-sm font-bold tabular-nums text-text">
                {item.count.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      </div>
    </PanelTransition>
  )
}

function RarityPanel({ viewModel }: { viewModel: OverviewHeroViewModel }) {
  const total = viewModel.rarityBuckets.reduce((sum, bucket) => sum + bucket.count, 0)
  const maxCount = Math.max(...viewModel.rarityBuckets.map((bucket) => bucket.count), 1)

  return (
    <PanelTransition>
      <div className="min-h-56">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
              已取得獎盃稀有度
            </p>
            <p className="mt-1 text-sm text-muted">{total.toLocaleString()} 座獎盃有稀有度資料</p>
          </div>
          <span className="rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 text-[10px] font-bold text-accent">
            來源 · {viewModel.raritySourceLabel}
          </span>
        </div>

        <div
          className="mt-5 flex flex-col gap-3"
          role="img"
          aria-label={`${viewModel.raritySourceLabel} 稀有度分布：${viewModel.rarityBuckets
            .map((bucket) => `${bucket.label} ${bucket.count}`)
            .join(', ')}`}
        >
          {viewModel.rarityBuckets.map((bucket) => (
            <div key={bucket.label} className="grid grid-cols-[5rem_minmax(0,1fr)_2.5rem] items-center gap-2">
              <span className="text-xs text-muted">{bucket.label}</span>
              <div className="h-2 overflow-hidden rounded-full bg-border/50">
                <div
                  className="h-full origin-left rounded-full bg-accent transition-transform duration-300 motion-reduce:transition-none"
                  style={{ transform: `scaleX(${bucket.count / maxCount})` }}
                />
              </div>
              <span className="text-right text-xs font-semibold tabular-nums text-text">
                {bucket.count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </PanelTransition>
  )
}

function RecentPanel({ viewModel }: { viewModel: OverviewHeroViewModel }) {
  return (
    <PanelTransition>
      <div className="min-h-56">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
          最近取得的獎盃
        </p>
        <ul className="flex flex-col gap-2">
          {viewModel.recentTrophies.map(({ trophy, earnedAt }) => {
            const rarity = viewModel.raritySource
              ? rarityForSource(trophy, viewModel.raritySource)
              : null
            return (
              <li
                key={`${trophy.game}-${trophy.title}-${trophy.timestamp}`}
                className="flex items-center gap-3 rounded-xl border border-border/70 bg-bg/35 p-2.5"
              >
                <ImageWithFallback
                  src={trophy.icon_url}
                  alt=""
                  loading="lazy"
                  className="h-10 w-10 shrink-0 rounded-lg border border-border object-cover"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-text" title={trophy.title}>
                    {trophy.title}
                  </p>
                  <p className="truncate text-[10px] text-muted" title={trophy.game}>
                    {trophy.game}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p
                    className="text-[10px] font-bold"
                    style={{ color: GRADE_COLOR_VAR[trophy.grade] }}
                  >
                    {GRADE_LABEL[trophy.grade]}
                  </p>
                  <p className="mt-0.5 text-[10px] text-muted">
                    {earnedAt.toLocaleDateString('zh-TW')}
                    {rarity ? ` · ${viewModel.raritySourceLabel} ${rarity}` : ''}
                  </p>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </PanelTransition>
  )
}

function InteractivePanel({ viewModel }: { viewModel: OverviewHeroViewModel }) {
  const tabs: { key: HeroTabKey; label: string }[] = [{ key: 'progress', label: '進度' }]
  if (viewModel.raritySource && viewModel.rarityBuckets.some((bucket) => bucket.count > 0)) {
    tabs.push({ key: 'rarity', label: '稀有度' })
  }
  if (viewModel.recentTrophies.length > 0) tabs.push({ key: 'recent', label: '最近取得' })

  if (tabs.length === 1) {
    return (
      <div className="h-full min-w-0 max-w-full overflow-hidden rounded-2xl border border-border/80 bg-bg/35 p-4 sm:p-5">
        <h2 className="mb-4 text-sm font-semibold text-text">玩家進度</h2>
        <ProgressPanel viewModel={viewModel} />
      </div>
    )
  }

  return (
    <div className="h-full min-w-0 max-w-full overflow-hidden rounded-2xl border border-border/80 bg-bg/35 p-3 sm:p-4">
      <Tabs
        defaultSelectedKey="progress"
        aria-label="玩家獎盃分析"
        variant="secondary"
        className="min-w-0 max-w-full"
      >
        <Tabs.ListContainer className="min-w-0 max-w-full">
          <Tabs.List
            className="grid min-w-0 w-full rounded-xl border border-border/70 bg-bg/55 p-1"
            style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}
          >
            {tabs.map((tab) => (
              <Tabs.Tab
                key={tab.key}
                id={tab.key}
                className="relative min-h-10 rounded-lg px-3 text-xs font-semibold text-muted outline-none transition data-[focus-visible]:ring-2 data-[focus-visible]:ring-accent data-[selected]:text-text"
              >
                <Tabs.Indicator className="absolute inset-0 -z-10 rounded-lg bg-accent/15 shadow-sm" />
                {tab.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs.ListContainer>
        <Tabs.Panel id="progress" className="px-1 pt-5 outline-none">
          <ProgressPanel viewModel={viewModel} />
        </Tabs.Panel>
        {tabs.some((tab) => tab.key === 'rarity') && (
          <Tabs.Panel id="rarity" className="px-1 pt-5 outline-none">
            <RarityPanel viewModel={viewModel} />
          </Tabs.Panel>
        )}
        {tabs.some((tab) => tab.key === 'recent') && (
          <Tabs.Panel id="recent" className="px-1 pt-5 outline-none">
            <RecentPanel viewModel={viewModel} />
          </Tabs.Panel>
        )}
      </Tabs>
    </div>
  )
}

export function OverviewHero({ data, refreshing, refreshError, onRefresh }: OverviewHeroProps) {
  const viewModel = useMemo(() => buildOverviewHeroViewModel(data), [data])
  const navigate = useNavigate()
  const prefersReducedMotion = useReducedMotion()
  const spotlight = useHeroSpotlight<HTMLElement>()
  const updatedAt = formatUpdatedAt(viewModel.fetchedAt)
  const profileBase = `/u/${encodeURIComponent(viewModel.username)}`

  const focusProfileSearch = () => {
    const input = document.getElementById('global-psn-id-search')
    input?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' })
    input?.focus()
  }

  return (
    <section
      ref={spotlight.ref}
      onPointerMove={spotlight.onPointerMove}
      onPointerLeave={spotlight.onPointerLeave}
      className="command-center-spotlight magic-grid relative isolate overflow-hidden rounded-3xl border border-border bg-surface p-5 shadow-2xl shadow-black/25 sm:p-6"
      aria-labelledby="profile-command-center-title"
    >
      <div aria-hidden="true" className="pointer-events-none absolute -left-24 -top-32 h-72 w-72 rounded-full bg-accent/8 blur-3xl" />
      <div aria-hidden="true" className="pointer-events-none absolute -bottom-36 right-0 h-72 w-72 rounded-full bg-platinum/5 blur-3xl" />
      <BorderBeam size={190} duration={13} borderWidth={1.25} />

      <div className="relative grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
        <div className="min-w-0">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <Avatar className="h-20 w-20 shrink-0 rounded-2xl border-2 border-accent/70 bg-bg shadow-[0_0_30px_rgba(245,179,1,0.16)] sm:h-24 sm:w-24">
              {viewModel.avatarUrl && (
                <Avatar.Image
                  src={viewModel.avatarUrl}
                  alt={`${viewModel.username} 的 PSN 個人圖片`}
                  className="h-full w-full object-cover"
                />
              )}
              <Avatar.Fallback className="text-3xl" aria-label="無法取得個人圖片">
                🏆
              </Avatar.Fallback>
            </Avatar>

            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent">
                獎盃玩家指揮中心
              </p>
              <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2">
                <h1
                  id="profile-command-center-title"
                  className="max-w-full truncate text-2xl font-black tracking-tight text-text sm:text-3xl"
                  title={viewModel.username}
                >
                  {viewModel.username}
                </h1>
                <span className="rounded-full border border-border bg-bg/55 px-2.5 py-1 text-[10px] font-bold text-muted">
                  {viewModel.sourceLabel}
                </span>
                {viewModel.cacheStatus !== 'unknown' && (
                  <span
                    className={[
                      'rounded-full border px-2.5 py-1 text-[10px] font-bold',
                      viewModel.cacheStatus === 'cached'
                        ? 'border-accent/30 bg-accent/10 text-accent'
                        : 'border-platinum/30 bg-platinum/10 text-platinum',
                    ].join(' ')}
                  >
                    {viewModel.cacheStatus === 'cached' ? '快取 · 24 小時' : '即時結果'}
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                {updatedAt && (
                  <time dateTime={viewModel.fetchedAt?.toISOString()}>更新時間：{updatedAt}</time>
                )}
                <button
                  type="button"
                  onClick={focusProfileSearch}
                  className="min-h-7 rounded-md font-semibold text-accent outline-none transition hover:text-accent-bright focus-visible:ring-2 focus-visible:ring-accent"
                >
                  切換玩家
                </button>
              </div>
            </div>

            <Button
              type="button"
              onPress={() => void onRefresh()}
              isDisabled={refreshing}
              isPending={refreshing}
              variant="outline"
              size="sm"
              className="min-h-11 shrink-0"
              aria-label="從設定的資料來源重新整理玩家資料"
            >
              {refreshing ? '同步中…' : '重新整理資料'}
            </Button>
          </div>

          <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center">
            <TrophyLevelGauge level={viewModel.level} progress={viewModel.levelProgress} />
            <div className="grid min-w-0 flex-1 grid-cols-2 gap-2">
              {viewModel.metrics.map((metric, index) => (
                <div key={metric.key} className="min-w-0 rounded-xl border border-border/75 bg-bg/35 p-3">
                  <p className="truncate text-[10px] font-semibold uppercase tracking-[0.13em] text-muted">
                    {metric.label}
                  </p>
                  <p className={`mt-1 truncate text-xl font-black tabular-nums sm:text-2xl ${TONE_CLASS[metric.tone]}`}>
                    {metric.numeric && typeof metric.value === 'number' ? (
                      <NumberTicker value={metric.value} delay={index * 0.04} />
                    ) : (
                      metric.value
                    )}
                  </p>
                  {metric.detail && <p className="mt-0.5 text-[10px] text-muted">{metric.detail}</p>}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5" aria-label="玩家功能頁面">
            <Button
              type="button"
              onPress={() => navigate(`${profileBase}/games`)}
              variant="primary"
              className="min-h-11"
            >
              查看遊戲
            </Button>
            <Button type="button" onPress={() => navigate(`${profileBase}/advisor`)} variant="outline" className="min-h-11">
              獎盃顧問
            </Button>
            <Button type="button" onPress={() => navigate(`${profileBase}/timeline`)} variant="outline" className="min-h-11">
              時間軸
            </Button>
            <Button type="button" onPress={() => navigate(`${profileBase}/milestones`)} variant="outline" className="min-h-11">
              里程碑
            </Button>
            <Button type="button" onPress={() => navigate(`${profileBase}/data`)} variant="ghost" className="min-h-11">
              資料
            </Button>
          </div>

          <div className="mt-4 min-h-5" aria-live="polite" aria-atomic="true">
            {refreshing ? (
              <p className="text-xs text-muted">正在背景同步，目前的玩家資料仍會保留顯示。</p>
            ) : refreshError ? (
              <p role="alert" className="text-xs text-bronze">
                重新整理失敗，目前仍顯示原有的玩家資料。
              </p>
            ) : viewModel.cacheStatus === 'cached' ? (
              <p className="text-xs text-muted">目前資料來自後端的 24 小時玩家快取。</p>
            ) : null}
          </div>
        </div>

        <InteractivePanel viewModel={viewModel} />
      </div>
    </section>
  )
}
