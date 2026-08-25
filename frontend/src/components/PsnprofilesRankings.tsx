import { Button } from '@heroui/react'
import { useMemo, useState } from 'react'
import type { ProfileSummary, PsnprofilesStats } from '../lib/api'
import { usePsnprofilesStats } from '../lib/queries'

function rankFromStats(summary: ProfileSummary): PsnprofilesStats | null {
  const world = Number.parseInt((summary.stats['World Rank'] ?? '').replaceAll(',', ''), 10)
  const countryEntry = Object.entries(summary.stats).find(
    ([label]) => !['World Rank', 'Level Rank'].includes(label) && label.endsWith(' Rank'),
  )
  const country = Number.parseInt((countryEntry?.[1] ?? '').replaceAll(',', ''), 10)
  if (!Number.isFinite(world) && !Number.isFinite(country)) return null

  return {
    world_rank: Number.isFinite(world) ? world : null,
    country_rank: Number.isFinite(country) ? country : null,
    country_label: countryEntry?.[0] ?? '全國排名',
    completion: summary.stats.Completion ?? null,
    profile_url: `https://psnprofiles.com/${encodeURIComponent(summary.username)}`,
  }
}

function formatRank(rank: number | null): string {
  return rank == null ? '無法取得' : `#${rank.toLocaleString()}`
}

export function PsnprofilesRankings({ summary }: { summary: ProfileSummary }) {
  const embedded = useMemo(() => rankFromStats(summary), [summary])
  const [requested, setRequested] = useState(false)
  const query = usePsnprofilesStats(summary.username, requested && !embedded)
  const rankings = embedded ?? query.data

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">PSNProfiles 排名</h2>
          <p className="mt-1 text-xs text-muted">
            僅代表 PSNProfiles 所追蹤的公開玩家，不是 Sony 官方排行榜。
          </p>
        </div>

        {!rankings && !requested && (
          <Button
            type="button"
            onPress={() => setRequested(true)}
            size="sm"
            variant="outline"
            className="text-xs"
          >
            載入排名
          </Button>
        )}
      </div>

      {requested && query.isFetching && (
        <p className="mt-4 text-sm text-muted">正在開啟 PSNProfiles 並載入排名…</p>
      )}

      {rankings && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <a
            href={rankings.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-border bg-bg/40 p-4 transition hover:border-accent"
          >
            <div className="text-2xl font-bold text-accent">{formatRank(rankings.world_rank)}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">全球排名</div>
          </a>
          <a
            href={rankings.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-border bg-bg/40 p-4 transition hover:border-accent"
          >
            <div className="text-2xl font-bold text-accent">{formatRank(rankings.country_rank)}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">
              全國排名
            </div>
          </a>
        </div>
      )}

      {requested && !query.isFetching && query.isSuccess && !rankings && (
        <div className="mt-4 flex items-center gap-3">
          <p className="text-sm text-muted">
            無法取得排名。玩家資料必須公開，且 PSNProfiles 上需要有國家／地區資訊。
          </p>
          <Button
            type="button"
            onPress={() => void query.refetch()}
            size="sm"
            variant="ghost"
            className="text-xs text-accent"
          >
            重試
          </Button>
        </div>
      )}
    </section>
  )
}
