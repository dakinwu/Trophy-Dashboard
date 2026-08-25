import { motion, useReducedMotion } from 'motion/react'

interface TrophyLevelGaugeProps {
  level: string | null
  progress: number | null
}

const RADIUS = 48
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function TrophyLevelGauge({ level, progress }: TrophyLevelGaugeProps) {
  const prefersReducedMotion = useReducedMotion()
  const normalizedProgress = progress === null ? null : Math.min(100, Math.max(0, progress))
  const offset =
    normalizedProgress === null
      ? CIRCUMFERENCE
      : CIRCUMFERENCE * (1 - normalizedProgress / 100)
  const label =
    normalizedProgress === null
      ? `獎盃等級 ${level ?? '無法取得'}；無法取得等級進度`
      : `獎盃等級 ${level ?? '無法取得'}；距離下一級 ${normalizedProgress}%`

  return (
    <div className="flex shrink-0 flex-col items-center gap-2">
      <div className="relative h-32 w-32" role="img" aria-label={label}>
        <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden="true">
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            fill="none"
            stroke="var(--border)"
            strokeWidth="7"
          />
          {normalizedProgress !== null && (
            <motion.circle
              cx="60"
              cy="60"
              r={RADIUS}
              fill="none"
              stroke="var(--accent)"
              strokeLinecap="round"
              strokeWidth="7"
              strokeDasharray={CIRCUMFERENCE}
              initial={prefersReducedMotion ? false : { strokeDashoffset: CIRCUMFERENCE }}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 0.65, ease: 'easeOut' }}
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
            等級
          </span>
          <span className="mt-0.5 max-w-20 truncate text-2xl font-black tabular-nums text-accent-bright">
            {level ?? '—'}
          </span>
          <span className="mt-0.5 text-[10px] text-muted">
            {normalizedProgress === null ? '進度無法取得' : `下一級 ${normalizedProgress}%`}
          </span>
        </div>
      </div>
    </div>
  )
}
