import { describe, expect, test } from 'vitest'
import {
  toAuthUser,
  toChatResult,
  toConversation,
  toLeaning,
  toSettings,
  toTemperament,
  toTrait,
  toUserSummary,
  toYouView,
} from '~/server/mappers'

describe('mappers', () => {
  test('maps an account to camelCase', () => {
    expect(
      toAuthUser({
        user_id: 'u1',
        email: 'a@b.co',
        onboarded: false,
        onboarding_step: 2,
      }),
    ).toEqual({
      userId: 'u1',
      email: 'a@b.co',
      onboarded: false,
      onboardingStep: 2,
    })
  })

  test('maps a temperament', () => {
    expect(
      toTemperament({
        id: 'steady',
        feels_like: 'Even, dry, observant',
        humor: 'Understatement',
        curiosity: 'How people decide, practical details',
        pushback: 'Plain, once, with a reason',
        pace: 'Unhurried',
        first_line: 'First line.',
        sample_reply: 'Sample.',
      }),
    ).toEqual({
      id: 'steady',
      feelsLike: 'Even, dry, observant',
      humor: 'Understatement',
      curiosity: 'How people decide, practical details',
      pushback: 'Plain, once, with a reason',
      pace: 'Unhurried',
      firstLine: 'First line.',
      sampleReply: 'Sample.',
    })
  })

  test('maps settings verbatim', () => {
    const api = {
      explicit: { address: 'Sam' },
      learned: { humor: 5 },
      effective: { warmth: 7, directness: 6 },
    }
    expect(toSettings(api)).toEqual(api)
  })

  test('maps traits and leanings, defaulting a missing last_landed to null', () => {
    expect(
      toTrait({
        id: 't1',
        kind: 'nickname',
        label: 'Doc',
        status: 'active',
        last_landed: null,
      }),
    ).toEqual({
      id: 't1',
      kind: 'nickname',
      label: 'Doc',
      status: 'active',
      lastLanded: null,
    })
    expect(
      toLeaning({
        id: 'l1',
        kind: 'humor_style',
        value: 'dry',
        status: 'tilt',
      }),
    ).toEqual({ id: 'l1', kind: 'humor_style', value: 'dry', status: 'tilt' })
  })

  test('maps the you view', () => {
    const view = toYouView(
      [
        {
          id: 't1',
          kind: 'nickname',
          label: 'Doc',
          status: 'active',
          last_landed: '2026-11-01T10:00:00',
        },
      ],
      [
        {
          id: 'l1',
          kind: 'humor_style',
          value: 'dry',
          status: 'tilt',
        },
      ],
      ['Prefers mornings'],
    )
    expect(view.traits[0]?.lastLanded).toBe('2026-11-01T10:00:00')
    expect(view.leanings[0]?.value).toBe('dry')
    expect(view.facts).toEqual(['Prefers mornings'])
  })

  test('drops the internal fields of a chat turn', () => {
    const result = toChatResult({
      thread_id: 'th1',
      turn_id: 'tu1',
      conversation_id: 'cv1',
      reply: 'Noted.',
      new_thread: true,
      memory_degraded: false,
      decisions: { mode: 'decide' },
      mode: 'decide',
      concern_tier: 'normal',
    })
    expect(result).toEqual({
      threadId: 'th1',
      turnId: 'tu1',
      reply: 'Noted.',
      newThread: true,
      memoryDegraded: false,
    })
    expect(Object.keys(result)).not.toContain('mode')
    expect(Object.keys(result)).not.toContain('decisions')
    expect(Object.keys(result)).not.toContain('concernTier')
  })

  test('maps a user summary and a conversation', () => {
    expect(
      toUserSummary({
        temperament: 'steady',
        locale: 'en-US',
        stage_permissions: 'words',
        dials_words: 'warm and steady',
        traits_count: 2,
        leanings: [],
      }),
    ).toEqual({
      temperament: 'steady',
      locale: 'en-US',
      stagePermissions: 'words',
      dialsWords: 'warm and steady',
      traitsCount: 2,
      leanings: [],
    })
    expect(
      toConversation({ conversation_id: 'cv1', first_message: 'Hello.' }),
    ).toEqual({ conversationId: 'cv1', firstMessage: 'Hello.' })
  })
})
