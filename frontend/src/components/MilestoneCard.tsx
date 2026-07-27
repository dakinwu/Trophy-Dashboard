import type { Milestone } from '../lib/milestones'

export function MilestoneCard({ milestone }: { milestone: Milestone }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-md shadow-black/10 transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="flex items-center gap-2">
        <span className="text-2xl" aria-hidden="true">
          {milestone.icon}
        </span>
        <h3 className="text-sm font-semibold text-text">{milestone.title}</h3>
      </div>
      <p className="truncate text-sm text-text" title={milestone.trophyTitle}>
        {milestone.trophyTitle}
      </p>
      <p className="truncate text-xs text-muted" title={milestone.game}>
        {milestone.game}
      </p>
      <p className="text-xs text-muted">
        {milestone.date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        })}
      </p>
    </div>
  )
}
