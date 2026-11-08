/** Only public Sony trophy artwork uses the durable local image store. */
export function cachedTrophyImageUrl(src: string): string {
  try {
    const url = new URL(src)
    const allowed =
      (url.hostname === 'image.api.playstation.com' && url.pathname.startsWith('/trophy/')) ||
      (url.hostname === 'psnobj.prod.dl.playstation.net' && url.pathname.startsWith('/psnobj/'))
    if (url.protocol === 'https:' && allowed) {
      return `/api/images/official?url=${encodeURIComponent(src)}`
    }
  } catch {
    // Existing fixtures and relative/static assets do not need an image proxy.
  }
  return src
}
