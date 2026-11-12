import { describe, expect, test } from 'vitest'
import {
  isTemperamentDefault,
  patchFromValues,
  valuesFromSettings,
} from '~/lib/settings'
import type { Settings } from '~/lib/types'

const stored: Settings = {
  explicit: { warmth: 8, address: 'Sam', length: 'brief' },
  learned: { humor: 5 },
  effective: {
    address: 'Sam',
    length: 'brief',
    warmth: 8,
    directness: 6,
    humor: 4,
    initiative: 3,
  },
}

describe('settings values', () => {
  test('reads the effective values and the explicit names', () => {
    const values = valuesFromSettings(stored)
    expect(values.warmth).toBe(8)
    expect(values.directness).toBe(6)
    expect(values.humor).toBe(4)
    expect(values.initiative).toBe(3)
    expect(values.length).toBe('brief')
    expect(values.address).toBe('Sam')
    expect(values.nickname).toBe('')
  })

  test('falls back to the defaults when nothing is set', () => {
    const values = valuesFromSettings(null)
    expect(values).toEqual({
      warmth: 7,
      directness: 6,
      humor: 4,
      initiative: 3,
      length: 'match',
      advice: 'ask_first',
      checkIns: 'off',
      emoji: 'never',
      address: '',
      nickname: '',
    })
  })

  test('patches only what changed', () => {
    const before = valuesFromSettings(stored)
    const after = { ...before, warmth: 7, address: 'Sammy' }
    expect(patchFromValues(after, before)).toEqual({
      warmth: 7,
      address: 'Sammy',
    })
  })

  test('patches nothing when nothing changed', () => {
    const before = valuesFromSettings(stored)
    expect(patchFromValues(before, before)).toEqual({})
  })

  test('marks the dials that are still the temperament default', () => {
    const values = valuesFromSettings(stored)
    expect(isTemperamentDefault(stored, 'warmth')).toBe(false)
    expect(isTemperamentDefault(stored, 'directness')).toBe(true)
    expect(isTemperamentDefault(stored, 'humor')).toBe(true)
    expect(values.warmth).toBe(8)
  })
})
