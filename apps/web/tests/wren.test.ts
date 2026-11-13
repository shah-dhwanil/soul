import { describe, expect, test, vi } from 'vitest'
import { resetLearnedAndReload } from '~/server/wren'
import { ACCESS_COOKIE, REFRESH_COOKIE, type CookieJar } from '~/server/session'

function jarWith(cookies: Record<string, string> = {}): CookieJar {
  const store = new Map(Object.entries(cookies))
  return {
    get: (name) => store.get(name),
    set: (name, value) => {
      store.set(name, value)
    },
    clear: (name) => {
      store.delete(name)
    },
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('resetLearned', () => {
  test('returns the settings as they now stand, not just the empty map', async () => {
    const cookies = jarWith({
      [ACCESS_COOKIE]: 'access-value',
      [REFRESH_COOKIE]: 'refresh-value',
    })
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/settings/reset-learned')) {
        return jsonResponse({ learned: {} })
      }
      if (url.endsWith('/auth/me')) {
        return jsonResponse({
          user_id: 'u1',
          email: 'a@b.co',
          onboarded: true,
          onboarding_step: 4,
        })
      }
      if (url.endsWith('/settings')) {
        return jsonResponse({
          explicit: { address: 'Sam', warmth: 8 },
          learned: {},
          effective: {
            address: 'Sam',
            warmth: 8,
            directness: 6,
            humor: 4,
            initiative: 3,
          },
        })
      }
      return jsonResponse({ code: 'not_found' }, 404)
    })

    const result = await resetLearnedAndReload(cookies, {
      fetchImpl: fetchImpl as unknown as typeof fetch,
      baseUrl: 'http://api.test',
    })

    expect(result.ok).toBe(true)
    if (!result.ok) return
    // What was set by hand survives the reset.
    expect(result.data.explicit.address).toBe('Sam')
    expect(result.data.explicit.warmth).toBe(8)
    expect(result.data.learned).toEqual({})
  })
})
