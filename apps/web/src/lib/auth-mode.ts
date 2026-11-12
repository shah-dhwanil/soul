import { describe, expect, test } from 'vitest'

/**
 * Which mode the sign-in screen opens in.
 *
 * Someone who arrived from "Begin" has no account yet, so the account form
 * is what they need first.
 */
export function defaultAuthMode(
  next: string | undefined,
): 'signin' | 'register' {
  return next === '/onboarding' ? 'register' : 'signin'
}
