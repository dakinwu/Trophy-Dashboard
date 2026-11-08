import { useState, type ComponentPropsWithoutRef } from 'react'
import { cachedTrophyImageUrl } from '../lib/images'

type FallbackKind = 'trophy' | 'game'

interface ImageWithFallbackProps
  extends Omit<ComponentPropsWithoutRef<'img'>, 'onError' | 'src'> {
  src: string | null | undefined
  fallbackKind?: FallbackKind
}

/**
 * Keeps an unavailable remote image from rendering the browser's broken-image
 * icon and alt text as part of the card layout.
 */
export function ImageWithFallback({
  src,
  alt = '',
  className = '',
  fallbackKind = 'trophy',
  ...props
}: ImageWithFallbackProps) {
  const [failure, setFailure] = useState<{
    source: string
    cached: boolean
    original: boolean
  } | null>(null)
  const cachedSrc = src ? cachedTrophyImageUrl(src) : ''
  const currentFailure = failure?.source === src ? failure : null
  const imageSrc = currentFailure?.cached ? src : cachedSrc

  if (!src || currentFailure?.original) {
    return (
      <div
        role={alt ? 'img' : undefined}
        aria-label={alt || undefined}
        className={`flex flex-col items-center justify-center gap-1 overflow-hidden bg-surface/80 text-3xl ${className}`}
        {...props}
      >
        <span aria-hidden="true">{fallbackKind === 'game' ? '🎮' : '🏆'}</span>
        <span aria-hidden="true" className="text-[9px] leading-tight text-muted">圖片暫缺</span>
      </div>
    )
  }

  return (
    <img
      {...props}
      src={imageSrc ?? undefined}
      alt={alt}
      className={className}
      onError={() => setFailure({
        source: src,
        cached: true,
        original: imageSrc === src,
      })}
    />
  )
}
