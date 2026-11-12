import {
  deleteCookie,
  getCookie,
  getRequestProtocol,
  setCookie,
} from '@tanstack/react-start/server'
import type { CookieJar, CookieOptions } from './session'

/**
 * The cookie jar backed by the current request.
 *
 * `Secure` is set whenever the request is over https. Local development runs
 * on http, where a `Secure` cookie would simply be dropped by the browser.
 */
export function createServerCookieJar(): CookieJar {
  const secure = (): boolean => {
    try {
      return getRequestProtocol() === 'https'
    } catch {
      return false
    }
  }

  const withDefaults = (options?: CookieOptions): CookieOptions => ({
    path: '/',
    httpOnly: true,
    sameSite: 'lax',
    secure: secure(),
    ...options,
  })

  return {
    get: (name) => getCookie(name),
    set: (name, value, options) =>
      setCookie(name, value, withDefaults(options)),
    clear: (name, options) =>
      deleteCookie(name, withDefaults({ maxAge: 0, ...options })),
  }
}
