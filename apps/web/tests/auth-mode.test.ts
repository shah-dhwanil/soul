import { describe, expect, test } from 'vitest'
import { defaultAuthMode } from '~/lib/auth-mode'

describe('auth screen mode', () => {
  test('a visitor from Begin is asked to make an account', () => {
    expect(defaultAuthMode('/onboarding')).toBe('register')
  })

  test('everyone else signs in first', () => {
    expect(defaultAuthMode(undefined)).toBe('signin')
    expect(defaultAuthMode('/chat')).toBe('signin')
  })
})
