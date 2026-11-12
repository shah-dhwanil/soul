/**
 * Where the API lives. Server-side only: the browser never sees this URL.
 */
const DEFAULT_API_URL = 'http://localhost:8000'

export function apiBaseUrl(): string {
  const fromProcess =
    typeof process !== 'undefined' ? process.env?.WREN_API_URL : undefined
  const fromImportMeta = (
    import.meta as unknown as { env?: Record<string, string | undefined> }
  ).env?.WREN_API_URL
  const raw = fromProcess ?? fromImportMeta ?? DEFAULT_API_URL
  return raw.replace(/\/+$/, '')
}
