/** Escapes a single CSV field per RFC 4180 (quotes values containing commas, quotes, or newlines). */
function escapeCsvField(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/** Builds a CSV string (CRLF line endings) from a header row and string-cell rows. */
export function toCsv(header: string[], rows: string[][]): string {
  return [header, ...rows].map((row) => row.map(escapeCsvField).join(',')).join('\r\n')
}

/** Triggers a browser download of `content` as a file named `filename`. */
export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
