import { createServerFn } from '@tanstack/react-start'
import type { ApiAuthUser, AuthUser, Result } from '~/lib/types'
import { callApi, type CallApiOptions } from './client'
import { toAuthUser } from './mappers'
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearAuthCookies,
  setAuthCookies,
  type CookieJar,
} from './session'
import { createServerCookieJar } from './server-cookies'

/**
 * Account auth.
 *
 * The tokens the API returns are moved straight into HttpOnly cookies here,
 * on the server. They never reach component JavaScript.
 */

/** The signed-in account, or null when there is no usable session. */
export async function fetchMe(
  cookies: CookieJar,
  options: Partial<CallApiOptions> = {},
): Promise<Result<AuthUser | null>> {
  const hasAccess = cookies.get(ACCESS_COOKIE)
  const hasRefresh = cookies.get(REFRESH_COOKIE)
  if (!hasAccess && !hasRefresh) {
    return { ok: true, data: null }
  }
  const result = await callApi<ApiAuthUser>('/v1/auth/me', {
    cookies,
    ...options,
  })
  if (!result.ok) {
    if (
      result.code === 'invalid_token' ||
      result.code === 'missing_token' ||
      result.code === 'invalid_refresh_token'
    ) {
      // The session is gone or cannot be renewed: signed out, not broken.
      return { ok: true, data: null }
    }
    return { ok: false, code: result.code, status: result.status }
  }
  return { ok: true, data: toAuthUser(result.data) }
}

export const register = createServerFn({ method: 'POST' })
  .validator((data: { email: string; password: string }) => data)
  .handler(async ({ data }): Promise<Result<AuthUser>> => {
    const cookies = createServerCookieJar()
    const result = await callApi<ApiAuthUser>('/v1/auth/register', {
      cookies,
      method: 'POST',
      auth: false,
      body: { email: data.email, password: data.password },
    })
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    setAuthCookies(cookies, {
      accessToken: result.data.access_token ?? '',
      refreshToken: result.data.refresh_token ?? '',
    })
    return { ok: true, data: toAuthUser(result.data) }
  })

export const login = createServerFn({ method: 'POST' })
  .validator((data: { email: string; password: string }) => data)
  .handler(async ({ data }): Promise<Result<AuthUser>> => {
    const cookies = createServerCookieJar()
    const result = await callApi<ApiAuthUser>('/v1/auth/login', {
      cookies,
      method: 'POST',
      auth: false,
      body: { email: data.email, password: data.password },
    })
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    setAuthCookies(cookies, {
      accessToken: result.data.access_token ?? '',
      refreshToken: result.data.refresh_token ?? '',
    })
    return { ok: true, data: toAuthUser(result.data) }
  })

export const logout = createServerFn({ method: 'POST' }).handler(
  async (): Promise<Result<null>> => {
    clearAuthCookies(createServerCookieJar())
    return { ok: true, data: null }
  },
)

export const me = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Result<AuthUser | null>> => {
    return fetchMe(createServerCookieJar())
  },
)

export const completeOnboarding = createServerFn({ method: 'POST' }).handler(
  async (): Promise<Result<null>> => {
    const cookies = createServerCookieJar()
    const result = await callApi<null>('/v1/auth/complete-onboarding', {
      cookies,
      method: 'POST',
    })
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: null }
  },
)
