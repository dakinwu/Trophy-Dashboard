import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { MilestoneCard } from '../components/MilestoneCard'
import { ProfileStateGate } from '../components/ProfileStateGate'
import type { Trophy } from '../lib/api'
import { computeMilestones } from '../lib/milestones'
import { useProfile } from '../lib/queries'

export function MilestonesPage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)

  return (
    <ProfileStateGate username={username} query={profileQuery}>
      {(data) => <MilestonesContent trophyLog={data.trophy_log} />}
    </ProfileStateGate>
  )
}

function MilestonesContent({ trophyLog }: { trophyLog: Trophy[] }) {
  const milestones = useMemo(() => computeMilestones(trophyLog), [trophyLog])

  if (milestones.length === 0) {
    return <ErrorState title="No milestones yet" message="This profile has no logged trophies." />
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold text-text">Milestones</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {milestones.map((milestone) => (
          <MilestoneCard key={milestone.key} milestone={milestone} />
        ))}
      </div>
    </div>
  )
}
