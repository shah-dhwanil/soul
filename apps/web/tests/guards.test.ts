import { describe, expect, test } from 'vitest'
import { guardRoute } from '~/lib/guards'
import type { AuthUser } from '~/lib/types'

const signedOut: AuthUser | null = null
const halfWay: AuthUser = {
  userId: 'u1',
  email: 'a@b.co',
  onboarded: false,
  onboardingStep: 1,
}
const finished: AuthUser = {
  userId: 'u1',
  email: 'a@b.co',
  onboarded: true,
  onboardingStep: 4,
}

describe('route guards', () => {
  test('guard_matrix', () => {
    const matrix: Array<[string, AuthUser | null, string | undefined]> = [
      ['/chat', signedOut, '/login?next=%2Fchat'],
      ['/settings', signedOut, '/login?next=%2Fsettings'],
      ['/you', signedOut, '/login?next=%2Fyou'],
      ['/onboarding', signedOut, '/login?next=%2Fonboarding'],
      ['/chat', halfWay, '/onboarding'],
      ['/settings', halfWay, '/onboarding'],
      ['/you', halfWay, '/onboarding'],
      ['/onboarding', halfWay, undefined],
      ['/chat', finished, undefined],
      ['/settings', finished, undefined],
      ['/you', finished, undefined],
      ['/onboarding', finished, '/chat'],
    ]

    for (const [path, me, expected] of matrix) {
      expect(guardRoute(path, me), `${path} for ${JSON.stringify(me)}`).toBe(
        expected,
      )
    }
  })
})
