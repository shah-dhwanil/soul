import { describe, expect, test } from 'vitest'
import { dialsFrom, startingBeat } from '~/lib/onboarding'
import type { AuthUser, Settings } from '~/lib/types'

const signedOut: AuthUser | null = null
const registered: AuthUser = {
  userId: 'u1',
  email: 'a@b.co',
  onboarded: false,
  onboardingStep: 0,
}
const seeded: AuthUser = {
  userId: 'u1',
  email: 'a@b.co',
  onboarded: false,
  onboardingStep: 1,
}
const named: AuthUser = { ...seeded, onboardingStep: 2 }
const tuned: AuthUser = { ...seeded, onboardingStep: 3 }

describe('onboarding resume', () => {
  test('starts at the account beat with no session', () => {
    expect(startingBeat(signedOut)).toBe('account')
  })

  test('starts at the account beat when only registered', () => {
    expect(startingBeat(registered)).toBe('account')
  })

  test('skips the duel once a temperament exists', () => {
    expect(startingBeat(seeded)).toBe('name')
  })

  test('pre-fills the dials once the name is set', () => {
    expect(startingBeat(named)).toBe('dials')
  })

  test('shows the opening reveal when the dials are tuned', () => {
    expect(startingBeat(tuned)).toBe('reveal')
  })
})

describe('dials', () => {
  test('reads the effective dials', () => {
    const settings: Settings = {
      explicit: {},
      learned: {},
      effective: { warmth: 8, directness: 5, humor: 3, initiative: 4 },
    }
    expect(dialsFrom(settings)).toEqual({
      warmth: 8,
      directness: 5,
      humor: 3,
      initiative: 4,
    })
  })

  test('falls back to the defaults when there are no settings yet', () => {
    expect(dialsFrom(null)).toEqual({
      warmth: 7,
      directness: 6,
      humor: 4,
      initiative: 3,
    })
  })
})
