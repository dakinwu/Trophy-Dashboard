import { useCallback, useEffect, useRef, type PointerEventHandler } from 'react'

function canUsePointerEffect(): boolean {
  return (
    window.matchMedia('(pointer: fine)').matches &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** Updates spotlight CSS variables without introducing pointer-position React state. */
export function useHeroSpotlight<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const frame = useRef<number | null>(null)

  const onPointerMove: PointerEventHandler<T> = useCallback((event) => {
    if (!canUsePointerEffect()) return
    const element = event.currentTarget
    const rect = element.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      element.style.setProperty('--hero-spotlight-x', `${x}px`)
      element.style.setProperty('--hero-spotlight-y', `${y}px`)
      element.style.setProperty('--hero-spotlight-opacity', '1')
    })
  }, [])

  const onPointerLeave: PointerEventHandler<T> = useCallback((event) => {
    event.currentTarget.style.setProperty('--hero-spotlight-opacity', '0')
  }, [])

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current)
    },
    [],
  )

  return { ref, onPointerMove, onPointerLeave }
}
