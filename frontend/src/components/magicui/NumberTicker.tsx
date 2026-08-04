import { useEffect, useRef, type ComponentPropsWithoutRef } from 'react'
import { useInView, useMotionValue, useReducedMotion, useSpring } from 'motion/react'

interface NumberTickerProps extends ComponentPropsWithoutRef<'span'> {
  value: number
  startValue?: number
  delay?: number
  decimalPlaces?: number
}

/** Magic UI NumberTicker, adapted to the dashboard's Vite setup. */
export function NumberTicker({
  value,
  startValue = 0,
  delay = 0,
  decimalPlaces = 0,
  className,
  ...props
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const motionValue = useMotionValue(prefersReducedMotion ? value : startValue)
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 })
  const isInView = useInView(ref, { once: true, margin: '0px' })

  useEffect(() => {
    if (!isInView) return

    const timer = window.setTimeout(
      () => motionValue.set(value),
      prefersReducedMotion ? 0 : delay * 1000,
    )
    return () => window.clearTimeout(timer)
  }, [delay, isInView, motionValue, prefersReducedMotion, value])

  useEffect(
    () =>
      springValue.on('change', (latest) => {
        if (!ref.current) return
        ref.current.textContent = Intl.NumberFormat('en-US', {
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces,
        }).format(Number(latest.toFixed(decimalPlaces)))
      }),
    [decimalPlaces, springValue],
  )

  useEffect(() => {
    const fallback = window.setTimeout(() => {
      if (!ref.current) return
      ref.current.textContent = Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      }).format(value)
    }, 900)
    return () => window.clearTimeout(fallback)
  }, [decimalPlaces, value])

  return (
    <span
      ref={ref}
      className={['inline-block tabular-nums tracking-wide', className].filter(Boolean).join(' ')}
      {...props}
    >
      {Intl.NumberFormat('en-US').format(prefersReducedMotion ? value : startValue)}
    </span>
  )
}
