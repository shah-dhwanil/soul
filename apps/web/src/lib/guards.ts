import type { AuthUser } from '~/lib/types'

/**
 * Where a visitor may be, and where they get sent instead.
 *
 * These are pure functions so the whole matrix can be tested without a
 * router or a browser.
 */

/** Routes that need a signed-in account. */
export const PROTECTED_PATHS = ['/chat', '/settings', '/you', '/onboarding'] as const

/** A redirect the router can act on. */
export type GuardRedirect = { href: string }

/** Signed out: send to the login page, remembering where they were going. */
export function requireAuth(
  nextPath: string,
  me: AuthUser | null,
): string | undefined {
  if (!me) {
    return `/login?next=${encodeURIComponent(nextPath)}`
  }
  return undefined
}

/** Already finished onboarding: there is nothing to onboard. */
export function redirectIfOnboarded(me: AuthUser | null): string | undefined {
  return me?.onboarded ? '/chat' : undefined
}

/**
 * The whole rule for one path:
 *
 * - no session -> `/login?next=…`
 * - signed in but not onboarded -> `/onboarding`
 * - onboarded and on `/onboarding` -> `/chat`
 * - otherwise stay put.
 */
export function guardRoute(
  path: string,
  me: AuthUser | null,
): string | undefined {
  const login = requireAuth(path, me)
  if (login) return login
  if (path === '/onboarding') return redirectIfOnboarded(me)
  return me?.onboarded ? undefined : '/onboarding'
}

/** The same rule, shaped for the router's `redirect()`. */
export function guardRedirect(
  path: string,
  me: AuthUser | null,
): GuardRedirect | undefined {
  const target = guardRoute(path, me)
  return target ? { href: target } : undefined
}
