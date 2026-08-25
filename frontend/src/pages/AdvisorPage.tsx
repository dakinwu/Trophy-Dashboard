import { Button, Input, ListBox, Select, Skeleton } from '@heroui/react'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AdvisorGameCard } from '../components/AdvisorGameCard'
import { ErrorState } from '../components/ErrorState'
import type { AdvisorBatchResponse, AdvisorBundleResult, AdvisorGame, PsnprofilesAdvisorSignals } from '../lib/api'
import { ApiError } from '../lib/api'
import {
  advisorCandidateKey,
  advisorSignalKey,
  filterAdvisorGames,
  sortAdvisorGames,
  toAdvisorCandidate,
  type AdvisorPlatformFilter,
  type AdvisorSortMode,
  type AdvisorSourceFilter,
  type AdvisorStatusFilter,
  type AdvisorWeights,
} from '../lib/advisor'
import {
  useAdvisorLibrary,
  useAdvisorSignals,
  useCachedAdvisorSignals,
  useRefreshAdvisorLibrary,
} from '../lib/queries'

const STATUS_OPTIONS: { id: AdvisorStatusFilter; label: string }[] = [
  { id: 'unplayed', label: '尚未遊玩' },
  { id: 'in_progress', label: '進行中' },
  { id: 'completed', label: '已完成' },
  { id: 'all', label: '所有狀態' },
]

const PLATFORM_OPTIONS: { id: AdvisorPlatformFilter; label: string }[] = [
  { id: 'all', label: '所有平台' },
  { id: 'PS5', label: 'PlayStation 5' },
  { id: 'PS4', label: 'PlayStation 4' },
  { id: 'PS3', label: 'PlayStation 3' },
]

const SOURCE_OPTIONS: { id: AdvisorSourceFilter; label: string }[] = [
  { id: 'all', label: '所有來源' },
  { id: 'purchased', label: '自行購買' },
  { id: 'ps_plus', label: 'PlayStation Plus' },
  { id: 'other', label: '其他授權' },
]

const SORT_OPTIONS: { id: AdvisorSortMode; label: string }[] = [
  { id: 'library', label: '收藏庫順序' },
  { id: 'score', label: '推薦分數' },
  { id: 'platinumAchievers', label: '白金玩家數最多' },
  { id: 'platinumRate', label: '白金率最高' },
  { id: 'progress', label: '我的進度' },
  { id: 'playtime', label: '我的遊玩時間' },
  { id: 'name', label: '遊戲名稱' },
]

type BatchSize = '8' | '24' | '50'

const BATCH_SIZE_OPTIONS: { id: BatchSize; label: string }[] = [
  { id: '8', label: '8 款（最快）' },
  { id: '24', label: '24 款' },
  { id: '50', label: '50 款（上限）' },
]

function AdvisorLoading({ username }: { username: string }) {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-live="polite">
      <section className="rounded-3xl border border-border bg-surface p-6">
        <Skeleton className="h-4 w-36 rounded-full" />
        <Skeleton className="mt-4 h-9 w-72 max-w-full rounded-lg" />
        <Skeleton className="mt-3 h-4 w-full max-w-2xl rounded-full" />
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-24 rounded-xl" />)}
        </div>
      </section>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((item) => <Skeleton key={item} className="h-96 rounded-2xl" />)}
      </div>
      <p className="sr-only">正在載入 {username} 的私人 PlayStation 收藏庫。</p>
    </div>
  )
}

function Metric({ label, value, accent = false }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-border/70 bg-bg/35 p-4">
      <p className={`text-2xl font-black tabular-nums ${accent ? 'text-accent-bright' : 'text-text'}`}>
        {value.toLocaleString()}
      </p>
      <p className="mt-1 text-xs uppercase tracking-wide text-muted">{label}</p>
    </div>
  )
}

function ChoiceSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: { id: T; label: string }[]
  onChange: (value: T) => void
}) {
  const labelId = `advisor-${label.toLocaleLowerCase().replaceAll(' ', '-')}`
  return (
    <div className="flex min-w-40 flex-1 flex-col gap-1.5">
      <span id={labelId} className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</span>
      <Select
        aria-labelledby={labelId}
        selectedKey={value}
        onSelectionChange={(key) => onChange(key as T)}
        variant="secondary"
      >
        <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
        <Select.Popover>
          <ListBox>
            {options.map((option) => (
              <ListBox.Item key={option.id} id={option.id} textValue={option.label}>
                {option.label}<ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
    </div>
  )
}

export function AdvisorPage() {
  const { username } = useParams<{ username: string }>()
  const libraryQuery = useAdvisorLibrary(username)
  const libraryCandidates = useMemo(
    () => libraryQuery.data?.games.map(toAdvisorCandidate) ?? [],
    [libraryQuery.data],
  )
  const cachedSignalsQuery = useCachedAdvisorSignals(username, libraryCandidates)
  const { refresh, refreshing, refreshError } = useRefreshAdvisorLibrary(username)
  const analysis = useAdvisorSignals()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<AdvisorStatusFilter>('unplayed')
  const [platform, setPlatform] = useState<AdvisorPlatformFilter>('all')
  const [source, setSource] = useState<AdvisorSourceFilter>('all')
  const [sortMode, setSortMode] = useState<AdvisorSortMode>('score')
  const [platinumRateWeight, setPlatinumRateWeight] = useState(65)
  const [batchSize, setBatchSize] = useState<BatchSize>('24')
  const [visibleLimit, setVisibleLimit] = useState(24)
  const [signalsByKey, setSignalsByKey] = useState<Map<string, PsnprofilesAdvisorSignals>>(new Map())
  const [bundlesByKey, setBundlesByKey] = useState<Map<string, AdvisorBundleResult>>(new Map())
  const [errorsByKey, setErrorsByKey] = useState<Map<string, string>>(new Map())
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkProgress, setBulkProgress] = useState<{ completed: number; total: number } | null>(null)
  const [bulkError, setBulkError] = useState<string | null>(null)

  useEffect(() => {
    setSignalsByKey(new Map())
    setBundlesByKey(new Map())
    setErrorsByKey(new Map())
  }, [username])

  useEffect(() => {
    const cachedResults = cachedSignalsQuery.data?.results
    if (!cachedResults) return
    setSignalsByKey((current) => {
      const next = new Map(current)
      for (const result of cachedResults) {
        if (result.signals) {
          next.set(
            advisorSignalKey(result.game, result.platform),
            result.signals,
          )
        }
      }
      return next
    })
    setBundlesByKey((current) => {
      const next = new Map(current)
      for (const result of cachedResults) {
        if (result.bundle) {
          next.set(advisorSignalKey(result.game, result.platform), result.bundle)
        }
      }
      return next
    })
    setErrorsByKey((current) => {
      const next = new Map(current)
      for (const result of cachedResults) {
        const key = advisorSignalKey(result.game, result.platform)
        if (result.error && !result.retryable) next.set(key, result.error)
        else if (result.signals || result.bundle?.complete) next.delete(key)
      }
      return next
    })
  }, [cachedSignalsQuery.data])

  const weights: AdvisorWeights = useMemo(
    () => ({
      platinumRate: platinumRateWeight,
      platinumAchievers: 100 - platinumRateWeight,
    }),
    [platinumRateWeight],
  )

  const visibleGames = useMemo(() => {
    if (!libraryQuery.data) return []
    const filtered = filterAdvisorGames(libraryQuery.data.games, { search, status, platform, source })
    return sortAdvisorGames(filtered, sortMode, signalsByKey, weights, bundlesByKey)
  }, [libraryQuery.data, search, status, platform, source, sortMode, signalsByKey, bundlesByKey, weights])

  useEffect(() => {
    setVisibleLimit(24)
  }, [search, status, platform, source, sortMode])

  const maxPlatinumAchievers = useMemo(
    () => Math.max(
      0,
      ...Array.from(signalsByKey.values(), (signals) => signals.platinum_achievers ?? 0),
      ...Array.from(bundlesByKey.values()).flatMap((bundle) =>
        bundle.children.map((child) => child.signals?.platinum_achievers ?? 0),
      ),
    ),
    [signalsByKey, bundlesByKey],
  )
  const pendingKeys = new Set(
    (analysis.variables ?? []).map((candidate) => advisorSignalKey(candidate.game, candidate.platform)),
  )

  if (!username) {
    return <ErrorState title="尚未選擇玩家" message="請先在上方搜尋你的 PSN ID，再開啟獎盃顧問。" />
  }
  if (libraryQuery.isLoading) return <AdvisorLoading username={username} />
  if (libraryQuery.isError) {
    const error = libraryQuery.error
    if (error instanceof ApiError && error.status === 403) {
      return <ErrorState title="無法讀取私人收藏庫" message="只有目前 NPSSO 所屬帳號能查看有效的數位收藏庫；其他公開玩家仍可使用總覽與遊戲頁面。" />
    }
    if (error instanceof ApiError && error.status === 503) {
      return <ErrorState title="無法讀取 PlayStation 收藏庫" message="請確認專案根目錄 .env 內的 PSN_NPSSO 仍有效，再重新嘗試。" />
    }
    return <ErrorState title="無法載入獎盃顧問" message="目前無法載入收藏庫資料，請稍後再試。" />
  }
  const library = libraryQuery.data
  if (!library) return <ErrorState title="沒有收藏庫資料" message="Sony 沒有回傳收藏庫內容。" />

  function mergeAnalysis(response: AdvisorBatchResponse) {
    setSignalsByKey((current) => {
      const next = new Map(current)
      for (const result of response.results) {
        if (result.signals) next.set(advisorSignalKey(result.game, result.platform), result.signals)
      }
      return next
    })
    setBundlesByKey((current) => {
      const next = new Map(current)
      for (const result of response.results) {
        const key = advisorSignalKey(result.game, result.platform)
        if (result.bundle) next.set(key, result.bundle)
      }
      return next
    })
    setErrorsByKey((current) => {
      const next = new Map(current)
      for (const result of response.results) {
        const key = advisorSignalKey(result.game, result.platform)
        if (result.error) next.set(key, result.error)
        else if (!result.signals && !result.bundle) next.set(key, '找不到相符的 PSNProfiles 獎盃列表。')
        else next.delete(key)
      }
      return next
    })
  }

  function applyAnalysis(games: AdvisorGame[]) {
    setBulkError(null)
    analysis.mutate(games.map(toAdvisorCandidate), {
      onSuccess: (response) => {
        mergeAnalysis(response)
        setSortMode('score')
      },
    })
  }

  const isGameAnalyzed = (game: AdvisorGame) => {
    const key = advisorCandidateKey(game)
    return signalsByKey.has(key) || bundlesByKey.get(key)?.complete === true
  }
  const unanalyzedGames = visibleGames.filter((game) =>
    !isGameAnalyzed(game) && !errorsByKey.has(advisorCandidateKey(game)),
  )
  const failedGames = visibleGames.filter((game) =>
    !isGameAnalyzed(game) && errorsByKey.has(advisorCandidateKey(game)),
  )
  const analyzedVisibleCount = visibleGames.filter(isGameAnalyzed).length
  const libraryAnalysisCounts = library.games.reduce(
    (counts, game) => {
      const key = advisorCandidateKey(game)
      if (isGameAnalyzed(game)) {
        counts.analyzed += 1
      } else if (errorsByKey.has(key)) {
        counts.failed += 1
      } else {
        counts.pending += 1
      }
      return counts
    },
    { analyzed: 0, failed: 0, pending: 0 },
  )
  const nextBatch = unanalyzedGames.slice(0, Number(batchSize))
  const analysisBusy = analysis.isPending || bulkAnalyzing

  async function applyAllAnalysis() {
    const candidates = [...unanalyzedGames]
    if (candidates.length === 0 || bulkAnalyzing) return
    setBulkAnalyzing(true)
    setBulkError(null)
    setBulkProgress({ completed: 0, total: candidates.length })
    try {
      for (let start = 0; start < candidates.length; start += 50) {
        const games = candidates.slice(start, start + 50)
        const response = await analysis.mutateAsync(games.map(toAdvisorCandidate))
        mergeAnalysis(response)
        const completed = Math.min(start + games.length, candidates.length)
        setBulkProgress({ completed, total: candidates.length })
        if (response.results.length > 0 && response.results.every((result) => result.error)) {
          setBulkError('PSNProfiles 未能完成這一批分析，已停止後續批次。')
          break
        }
      }
      setSortMode('score')
    } catch {
      setBulkError('PSNProfiles 分析失敗，請稍後再試。')
    } finally {
      setBulkAnalyzing(false)
    }
  }

  const updated = library.fetched_at
    ? new Date(library.fetched_at).toLocaleString('zh-TW')
    : '無法取得'

  return (
    <div className="flex flex-col gap-6">
      <section className="relative overflow-hidden rounded-3xl border border-border bg-surface p-5 shadow-xl shadow-black/20 sm:p-6">
        <div aria-hidden="true" className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(245,179,1,0.12),transparent_45%)]" />
        <div className="relative">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">收藏庫決策中心</p>
              <h1 className="mt-2 text-2xl font-black text-text sm:text-3xl">獎盃顧問</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                從 {library.username} 目前有效的 PlayStation 數位收藏庫中挑選下一款遊戲，包含從未啟動過的作品。
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full border border-platinum/30 bg-platinum/10 px-3 py-1.5 font-semibold text-platinum">PSN 官方收藏庫</span>
              <span className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1.5 font-semibold text-accent">
                {library.title_resolver === 'gemini' ? 'Gemini 英文名稱解析' : '尚未設定 Gemini'}
              </span>
              <span className="rounded-full border border-border bg-bg/40 px-3 py-1.5 text-muted">{library.cache_status === 'cached' ? '快取 · 最長 24 小時' : '即時結果'}</span>
              <Button type="button" onPress={() => refresh()} isPending={refreshing} isDisabled={refreshing} size="sm" variant="outline">重新整理收藏庫</Button>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Metric label="有效收藏" value={library.total_count} accent />
            <Metric label="尚未遊玩" value={library.unplayed_count} />
            <Metric label="進行中" value={library.in_progress_count} />
            <Metric label="已完成" value={library.completed_count} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted">
            更新時間：{updated}。實體光碟與失效授權可能不會出現；跨世代 PS4、PS5 版本會合併顯示，PS3 遊玩時間可能無法取得。
            {library.excluded_trial_count > 0 && ` 已自動排除 ${library.excluded_trial_count.toLocaleString()} 款試玩、Demo、Beta 或測試版本。`}
            {library.excluded_content_count > 0 && ` 已自動排除 ${library.excluded_content_count.toLocaleString()} 款附加內容、原聲帶或非遊戲影音 App。`}
            {library.excluded_platinum_count > 0 && ` 已自動排除 ${library.excluded_platinum_count.toLocaleString()} 款你已取得白金獎盃的遊戲。`}
            {library.merged_platform_count > 0 && ` 已將 ${library.merged_platform_count.toLocaleString()} 個重複的跨平台版本合併到同一款遊戲。`}
          </p>
          {refreshError && <p role="status" className="mt-2 text-xs text-red-300">重新整理失敗，目前仍保留原有資料。</p>}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-text">推薦權重</h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">推薦分數以 PSNProfiles 白金率與白金玩家數為準。下方百分比是你設定的公式權重，不是外部統計；白金玩家數會做對數縮放，避免熱門遊戲完全壓過其他作品。沒有白金或缺少白金資料的遊戲不會用一般完成率硬算分數。</p>
          </div>
          <div className="grid min-w-64 grid-cols-3 overflow-hidden rounded-xl border border-border bg-bg/35 text-center">
            <div className="px-3 py-2">
              <p className="text-[10px] text-muted">已取得</p>
              <p className="text-xl font-black tabular-nums text-accent-bright">{libraryAnalysisCounts.analyzed.toLocaleString()}</p>
            </div>
            <div className="border-x border-border px-3 py-2">
              <p className="text-[10px] text-muted">目前失敗</p>
              <p className="text-xl font-black tabular-nums text-red-300">{libraryAnalysisCounts.failed.toLocaleString()}</p>
            </div>
            <div className="px-3 py-2">
              <p className="text-[10px] text-muted">待分析</p>
              <p className="text-xl font-black tabular-nums text-platinum">{libraryAnalysisCounts.pending.toLocaleString()}</p>
            </div>
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="rounded-xl border border-border/70 bg-bg/35 p-4">
            <span className="flex items-center justify-between text-sm font-semibold text-text"><span>白金率（推薦權重）</span><span className="tabular-nums text-accent">{platinumRateWeight}%</span></span>
            <input className="mt-4 w-full accent-[var(--accent)]" type="range" min="0" max="100" step="5" value={platinumRateWeight} onChange={(event) => setPlatinumRateWeight(Number(event.target.value))} />
          </label>
          <div className="rounded-xl border border-border/70 bg-bg/35 p-4">
            <span className="flex items-center justify-between text-sm font-semibold text-text"><span>白金玩家數（推薦權重）</span><span className="tabular-nums text-platinum">{100 - platinumRateWeight}%</span></span>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-border"><div className="h-full bg-platinum transition-[width]" style={{ width: `${100 - platinumRateWeight}%` }} /></div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-border bg-surface p-4">
          <div className="min-w-52 flex-[2]">
            <label htmlFor="advisor-search" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">搜尋收藏庫</label>
            <Input id="advisor-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="輸入遊戲名稱…" variant="secondary" fullWidth />
          </div>
          <ChoiceSelect label="狀態" value={status} options={STATUS_OPTIONS} onChange={setStatus} />
          <ChoiceSelect label="平台" value={platform} options={PLATFORM_OPTIONS} onChange={setPlatform} />
          <ChoiceSelect label="來源" value={source} options={SOURCE_OPTIONS} onChange={setSource} />
          <ChoiceSelect label="排序" value={sortMode} options={SORT_OPTIONS} onChange={setSortMode} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">
            符合條件：<span className="font-bold tabular-nums text-text">{visibleGames.length.toLocaleString()}</span> 款
            <span className="mx-2 text-border">·</span>
            已取得 <span className="font-semibold tabular-nums text-accent">{analyzedVisibleCount.toLocaleString()}</span>
            <span className="mx-2 text-border">·</span>
            目前失敗 <span className="font-semibold tabular-nums text-red-300">{failedGames.length.toLocaleString()}</span>
            <span className="mx-2 text-border">·</span>
            待分析 <span className="font-semibold tabular-nums text-platinum">{unanalyzedGames.length.toLocaleString()}</span>
          </p>
          <div className="flex flex-col items-end gap-2">
            <div className="flex flex-wrap items-end justify-end gap-2">
              <ChoiceSelect label="每批分析數量" value={batchSize} options={BATCH_SIZE_OPTIONS} onChange={setBatchSize} />
              <Button type="button" onPress={() => applyAnalysis(nextBatch)} isPending={analysis.isPending && !bulkAnalyzing} isDisabled={analysisBusy || nextBatch.length === 0} variant="primary" className="min-h-11">分析接下來 {nextBatch.length || 0} 款</Button>
              <Button type="button" onPress={() => void applyAllAnalysis()} isPending={bulkAnalyzing} isDisabled={analysisBusy || unanalyzedGames.length === 0} variant="outline" className="min-h-11">分析全部尚未分析項目（{unanalyzedGames.length}）</Button>
            </div>
            {bulkProgress && bulkAnalyzing && <span className="text-[10px] text-accent">分析進度：{bulkProgress.completed}／{bulkProgress.total}</span>}
            <span className="text-[10px] text-muted">待分析清單先顯示 Sony 收藏庫原名；分析成功後圖卡會以 PSNProfiles 英文媒合名稱為主，並保留 Sony 原名供核對。單一安全批次上限為 50 款，同一批會共用一個瀏覽器工作階段。</span>
          </div>
        </div>
        {(unanalyzedGames.length > 0 || failedGames.length > 0) && (
          <div className="grid gap-3 lg:grid-cols-2">
            {unanalyzedGames.length > 0 && (
              <details className="group rounded-xl border border-border bg-surface">
                <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
                  <span>查看待分析清單</span>
                  <span className="text-xs tabular-nums text-muted">下一批 {nextBatch.length}／共 {unanalyzedGames.length} 款</span>
                </summary>
                <ol className="max-h-72 space-y-1 overflow-y-auto border-t border-border p-3">
                  {unanalyzedGames.map((game, index) => (
                    <li key={game.title_id} className="flex items-center gap-3 rounded-lg bg-bg/35 px-3 py-2 text-xs">
                      <span className="w-6 shrink-0 text-right tabular-nums text-muted">{index + 1}</span>
                      <span className="min-w-0 flex-1 truncate font-semibold text-text" title={game.name}>{game.name}</span>
                      <span className="shrink-0 text-[10px] text-muted">{game.platform}</span>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${index < nextBatch.length ? 'bg-accent/15 text-accent-bright' : 'bg-platinum/10 text-platinum'}`}>
                        {index < nextBatch.length ? '下一批' : '後續批次'}
                      </span>
                    </li>
                  ))}
                </ol>
              </details>
            )}
            {failedGames.length > 0 && (
              <details className="group rounded-xl border border-red-300/20 bg-red-300/5">
                <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-red-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300">
                  <span>查看目前失敗項目</span>
                  <span className="text-xs tabular-nums text-red-200/70">{failedGames.length} 款</span>
                </summary>
                <ul className="max-h-72 space-y-1 overflow-y-auto border-t border-red-300/20 p-3">
                  {failedGames.map((game) => (
                    <li key={game.title_id} className="rounded-lg bg-bg/35 px-3 py-2 text-xs">
                      <div className="flex items-center justify-between gap-3">
                        <span className="min-w-0 truncate font-semibold text-text" title={game.name}>{game.name}</span>
                        <span className="shrink-0 text-[10px] text-muted">{game.platform}</span>
                      </div>
                      <p className="mt-1 leading-5 text-red-200/80">{errorsByKey.get(advisorCandidateKey(game))}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
        {(analysis.isError || bulkError) && <p role="status" className="rounded-xl border border-red-400/30 bg-red-400/10 p-3 text-xs text-red-200">{bulkError ?? 'PSNProfiles 分析失敗，請稍後再試。'}</p>}

        {visibleGames.length === 0 ? (
          <p className="rounded-2xl border border-border bg-surface p-6 text-sm text-muted">沒有符合目前篩選條件的遊戲。</p>
        ) : (
          <div className="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {visibleGames.slice(0, visibleLimit).map((game) => {
              const key = advisorCandidateKey(game)
              const signals = signalsByKey.get(key)
              const bundle = bundlesByKey.get(key)
              return (
                <AdvisorGameCard
                  key={game.title_id}
                  game={game}
                  signals={signals}
                  bundle={bundle}
                  weights={weights}
                  maxPlatinumAchievers={maxPlatinumAchievers}
                  analyzing={analysis.isPending && pendingKeys.has(key)}
                  analysisDisabled={analysisBusy}
                  analysisError={errorsByKey.get(key)}
                  onAnalyze={() => applyAnalysis([game])}
                />
              )
            })}
          </div>
        )}
        {visibleLimit < visibleGames.length && (
          <Button
            type="button"
            onPress={() => setVisibleLimit((current) => current + 24)}
            variant="outline"
            className="mx-auto min-h-11 min-w-44"
          >
            再顯示 24 款
          </Button>
        )}
      </section>
    </div>
  )
}
