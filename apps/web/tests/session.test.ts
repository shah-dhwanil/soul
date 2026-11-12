import { describe, expect, test, vi } from 'vitest'
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  parseCookieHeader,
  serializeCookie,
} from '~/server/session'
import { callApi } from '~/server/client'
import { fetchMe } from '~/server/auth'
import type { CookieJar } from '~/server/session'

function jarWith(cookies: Record<string, string> = {}): CookieJar & {
  store: Map<string, string>
} {
  const store = new Map(Object.entries(cookies))
  return {
    store,
    get: (name) => store.get(name),
    set: (name, value) => {
      store.set(name, value)
    },
    clear: (name) => {
      store.delete(name)
    },
  }
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('cookie helpers', () => {
  test('parses and serializes cookie values', () => {
    const header = `${ACCESS_COOKIE}=access-value; ${REFRESH_COOKIE}=refresh-value`
    const parsed = parseCookieHeader(header)

    expect(parsed[ACCESS_COOKIE]).toBe('access-value')
    expect(parsed[REFRESH_COOKIE]).toBe('refresh-value')

    const serialized = serializeCookie(ACCESS_COOKIE, parsed[ACCESS_COOKIE], {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
    })
    expect(serialized).toContain(`${ACCESS_COOKIE}=access-value`)
    expect(serialized).toContain('HttpOnly')
    expect(serialized).toContain('SameSite=Lax')
    expect(parseCookieHeader(serialized.split(';')[0]!)[ACCESS_COOKIE]).toBe(
      'access-value',
    )
  })
})

describe('callApi refresh rule', () => {
  test('refreshes once on 401', async () => {
    const cookies = jarWith({
      [ACCESS_COOKIE]: 'stale-access',
      [REFRESH_COOKIE]: 'good-refresh',
    })
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.endsWith('/v1/auth/refresh')) {
        return jsonResponse({ access_token: 'fresh-access' }, 200)
      }
      const auth = (init?.headers as Record<string, string>)?.['authorization']
      if (auth === 'Bearer stale-access') {
        return jsonResponse({ code: 'invalid_token' }, 401)
      }
      return jsonResponse({ reply: 'hello' }, 200)
    })

    const result = await callApi<{ reply: string }>('/v1/chat', {
      cookies,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      baseUrl: 'http://api.test',
      method: 'POST',
      body: { message: 'hi' },
    })

    expect(result).toEqual({ ok: true, data: { reply: 'hello' } })
    expect(cookies.get(ACCESS_COOKIE)).toBe('fresh-access')
    expect(
      fetchImpl.mock.calls.filter((c) => String(c[0]).endsWith('/v1/auth/refresh')),
    ).toHaveLength(1)
  })

  test('does not retry twice', async () => {
    const cookies = jarWith({
      [ACCESS_COOKIE]: 'stale-access',
      [REFRESH_COOKIE]: 'good-refresh',
    })
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/v1/auth/refresh')) {
        return jsonResponse({ access_token: 'fresh-access' }, 200)
      }
      return jsonResponse({ code: 'invalid_token' }, 401)
    })

    const result = await callApi('/v1/chat', {
      cookies,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      baseUrl: 'http://api.test',
      method: 'POST',
      body: { message: 'hi' },
    })

    expect(result).toEqual({ ok: false, code: 'invalid_token', status: 401 })
    expect(
      fetchImpl.mock.calls.filter((c) => String(c[0]).endsWith('/v1/auth/refresh')),
    ).toHaveLength(1)
  })
})

describe('me', () => {
  test('returns null without cookies', async () => {
    const cookies = jarWith()
    const fetchImpl = vi.fn()

    const result = await fetchMe(cookies, {
      fetchImpl: fetchImpl as unknown as typeof fetch,
      baseUrl: 'http://api.test',
    })

    expect(result).toEqual({ ok: true, data: null })
    expect(fetchImpl).not.toHaveBeenCalled()
  })
})
