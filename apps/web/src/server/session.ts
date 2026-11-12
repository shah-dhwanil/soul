/**
 * Session cookies.
 *
 * The access token (`wren_at`) and the refresh token (`wren_rt`) live only in
 * first-party HttpOnly cookies: never in `localStorage`, never readable from
 * component JavaScript. The refresh cookie is what lets an expired access
 * token be replaced mid-session without the user noticing.
 */

export const ACCESS_COOKIE = 'wren_at'
export const REFRESH_COOKIE = 'wren_rt'

/** Access tokens last 15 minutes; refresh tokens last 30 days. */
export const ACCESS_TTL_SECONDS = 15 * 60
export const REFRESH_TTL_SECONDS = 30 * 24 * 60 * 60

export type SameSite = 'lax' | 'strict' | 'none'

export interface CookieOptions {
  path?: string
  httpOnly?: boolean
  secure?: boolean
  sameSite?: SameSite
  maxAge?: number
}

export interface CookieJar {
  get(name: string): string | undefined
  set(name: string, value: string, options?: CookieOptions): void
  clear(name: string, options?: CookieOptions): void
}

/** Parse a `Cookie` header into name/value pairs. */
export function parseCookieHeader(
  header: string | undefined | null,
): Record<string, string> {
  const out: Record<string, string> = {}
  if (!header) return out
  for (const part of header.split(';')) {
    const index = part.indexOf('=')
    if (index === -1) continue
    const name = part.slice(0, index).trim()
    if (!name) continue
    const value = part.slice(index + 1).trim()
    out[name] = value
  }
  return out
}

/** Serialize one cookie into a `Set-Cookie` header value. */
export function serializeCookie(
  name: string,
  value: string,
  options: CookieOptions = {},
): string {
  const parts = [`${name}=${value}`]
  parts.push(`Path=${options.path ?? '/'}`)
  if (options.httpOnly) parts.push('HttpOnly')
  if (options.secure) parts.push('Secure')
  if (options.sameSite) {
    parts.push(
      `SameSite=${options.sameSite.charAt(0).toUpperCase()}${options.sameSite.slice(1)}`,
    )
  }
  if (typeof options.maxAge === 'number') {
    parts.push(`Max-Age=${options.maxAge}`)
  }
  return parts.join('; ')
}

export function accessToken(cookies: CookieJar): string | undefined {
  return cookies.get(ACCESS_COOKIE)
}

export function refreshToken(cookies: CookieJar): string | undefined {
  return cookies.get(REFRESH_COOKIE)
}

/** Put both tokens in the jar as first-party HttpOnly cookies. */
export function setAuthCookies(
  cookies: CookieJar,
  tokens: { accessToken: string; refreshToken: string },
  options: CookieOptions = {},
): void {
  cookies.set(ACCESS_COOKIE, tokens.accessToken, {
    httpOnly: true,
    sameSite: 'lax',
    maxAge: ACCESS_TTL_SECONDS,
    ...options,
  })
  cookies.set(REFRESH_COOKIE, tokens.refreshToken, {
    httpOnly: true,
    sameSite: 'lax',
    maxAge: REFRESH_TTL_SECONDS,
    ...options,
  })
}

/** Forget both tokens. */
export function clearAuthCookies(
  cookies: CookieJar,
  options: CookieOptions = {},
): void {
  cookies.clear(ACCESS_COOKIE, options)
  cookies.clear(REFRESH_COOKIE, options)
}
