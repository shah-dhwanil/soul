import type { AuthUser, Dials, Settings } from '~/lib/types'

/**
 * The pure parts of the onboarding arc: where an account resumes, and what
 * the dials start from.
 */

export type BeatKey =
  | 'account'
  | 'meet'
  | 'duel'
  | 'name'
  | 'dials'
  | 'reveal'

/** Where the arc starts for this account. */
export function startingBeat(user: AuthUser | null): BeatKey {
  if (!user) return 'account'
  // Step 0: the account exists, the persona does not yet.
  if (user.onboardingStep < 1) return 'account'
  if (user.onboardingStep < 2) return 'name'
  if (user.onboardingStep < 3) return 'dials'
  return 'reveal'
}

/** The dials as they stand now, with the temperament defaults as a floor. */
export function dialsFrom(settings: Settings | null): Dials {
  const effective = settings?.effective ?? {}
  const read = (key: string, fallback: number): number => {
    const value = effective[key]
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback
  }
  return {
    warmth: read('warmth', 7),
    directness: read('directness', 6),
    humor: read('humor', 4),
    initiative: read('initiative', 3),
  }
}
