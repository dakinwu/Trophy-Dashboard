import { useCallback, type PointerEvent, type ReactNode } from 'react'
import { motion, useMotionTemplate, useMotionValue, useReducedMotion } from 'motion/react'

interface MagicCardProps {
  children: ReactNode
  className?: string
  gradientSize?: number
  gradientFrom?: string
  gradientTo?: string
}

/** Magic UI-style cursor spotlight card, tailored to the dashboard palette. */
export function MagicCard({
  children,
  className,
  gradientSize = 170,
  gradientFrom = 'rgba(255, 207, 63, 0.7)',
  gradientTo = 'rgba(90, 182, 240, 0.35)',
}: MagicCardProps) {
  const prefersReducedMotion = useReducedMotion()
  const mouseX = useMotionValue(-gradientSize)
  const mouseY = useMotionValue(-gradientSize)
  const border = useMotionTemplate`radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, ${gradientFrom}, ${gradientTo}, var(--border) 75%)`
  const glow = useMotionTemplate`radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, rgba(245, 179, 1, 0.12), transparent 70%)`

  const reset = useCallback(() => {
    mouseX.set(-gradientSize)
    mouseY.set(-gradientSize)
  }, [gradientSize, mouseX, mouseY])

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (prefersReducedMotion) return
    const rect = event.currentTarget.getBoundingClientRect()
    mouseX.set(event.clientX - rect.left)
    mouseY.set(event.clientY - rect.top)
  }

  return (
    <motion.div
      className={['group relative isolate overflow-hidden rounded-xl p-px', className]
        .filter(Boolean)
        .join(' ')}
      onPointerMove={handlePointerMove}
      onPointerLeave={reset}
      style={{ background: prefersReducedMotion ? 'var(--border)' : border }}
    >
      <div className="relative h-full overflow-hidden rounded-[calc(0.75rem-1px)] bg-surface">
        {!prefersReducedMotion && (
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ background: glow }}
          />
        )}
        <div className="relative h-full">{children}</div>
      </div>
    </motion.div>
  )
}
