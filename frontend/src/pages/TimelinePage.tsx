import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { CalendarHeatmap } from '../components/charts/CalendarHeatmap'
import { MonthlyTrophyChart } from '../components/charts/MonthlyTrophyChart'
import { ErrorState } from '../components/ErrorState'
import { ProfileStateGate } from '../components/ProfileStateGate'
import type { Trophy } from '../lib/api'
import { useProfile } from '../lib/queries'
import { getDailyActivityMap, getMonthlyGradeCounts, getStreakStats } from '../lib/timeline'

export function TimelinePage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)

  return (
    <ProfileStateGate username={username} query={profileQuery}>
      {(data) => <TimelineContent trophyLog={data.trophy_log} />}
    </ProfileStateGate>
  )
}

function TimelineContent({ trophyLog }: { trophyLog: Trophy[] }) {
  const monthlyData = useMemo(() => getMonthlyGradeCounts(trophyLog), [trophyLog])
  const dailyActivity = useMemo(() => getDailyActivityMap(trophyLog), [trophyLog])
  const streaks = useMemo(() => getStreakStats(dailyActivity), [dailyActivity])

  if (trophyLog.length === 0) {
    return <ErrorState title="No trophies yet" message="This profile has no logged trophies." />
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-2xl border border-border bg-surface p-5">
        <h2 className="mb-4 text-lg font-semibold text-text">Trophies Earned Per Month</h2>
        <MonthlyTrophyChart data={monthlyData} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="rounded-2xl border border-border bg-surface p-5">
          <h2 className="mb-4 text-lg font-semibold text-text">Activity Calendar</h2>
          <CalendarHeatmap dailyActivity={dailyActivity} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-border bg-surface p-4 text-center shadow-md shadow-black/10">
            <div className="text-2xl font-bold text-accent-bright">{streaks.longest}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">
              Longest Streak (days)
            </div>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4 text-center shadow-md shadow-black/10">
            <div className="text-2xl font-bold text-accent-bright">{streaks.current}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-muted">
              Current Streak (days)
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
