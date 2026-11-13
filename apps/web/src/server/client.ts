import type { Result } from '~/lib/types'
import { apiBaseUrl } from './config'
import {
  ACCESS_COOKIE,
  ACCESS_TTL_SECONDS,
  REFRESH_COOKIE,
  type CookieJar,
} from './session'

/**
 * The one way this app talks to the API.
 *
 * The browser never calls FastAPI directly: every request goes through a
 * server function, which attaches the access token from the HttpOnly cookie.
 * If the access token has expired, the refresh cookie buys exactly one
 * silent retry.
 */

/** The API could not be reached at all. */
export const NETWORK_ERROR = 'network_error'

/** Raised internally when the API cannot be reached; never crosses a boundary. */
class NetworkError extends Error {}

export interface CallApiOptions {
  cookies: CookieJar
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  /** Send the access token. Defaults to true. */
  auth?: boolean
  headers?: Record<string, string>
  /** Injected in tests; defaults to the global fetch. */
  fetchImpl?: typeof fetch
  /** Injected in tests; defaults to the configured API URL. */
  baseUrl?: string
}

interface ErrorBody {
  code?: string
}

async function readResult<T>(response: Response): Promise<Result<T>> {
  if (response.status === 204) {
    return { ok: true, data: null as T }
  }
  let body: unknown = null
  const text = await response.text()
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }
  if (!response.ok) {
    const code =
      typeof (body as ErrorBody | null)?.code === 'string'
        ? (body as ErrorBody).code!
        : `http_${response.status}`
    return { ok: false, code, status: response.status }
  }
  return { ok: true, data: body as T }
}

/**
 * Trade the refresh cookie for a fresh access token.
 *
 * The new access token replaces the old one in the jar, so the next request
 * in this session is already authenticated.
 */
async function refreshAccessToken(
  cookies: CookieJar,
  fetchImpl: typeof fetch,
  baseUrl: string,
): Promise<
  | { ok: true; token: string }
  | { ok: false; code: string; status: number }
> {
  const refresh = cookies.get(REFRESH_COOKIE)
  if (!refresh) {
    return { ok: false, code: 'invalid_refresh_token', status: 401 }
  }
  let response: Response
  try {
    response = await fetchImpl(`${baseUrl}/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
  } catch {
    return { ok: false, code: NETWORK_ERROR, status: 0 }
  }
  const parsed = await readResult<{ access_token?: string }>(response)
  if (!parsed.ok) {
    return { ok: false, code: parsed.code, status: parsed.status }
  }
  const token = parsed.data?.access_token
  if (!token) {
    return { ok: false, code: 'invalid_refresh_token', status: 401 }
  }
  cookies.set(ACCESS_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    maxAge: ACCESS_TTL_SECONDS,
  })
  return { ok: true, token }
}

export async function callApi<T>(
  path: string,
  options: CallApiOptions,
): Promise<Result<T>> {
  const baseUrl = options.baseUrl ?? apiBaseUrl()
  const fetchImpl = options.fetchImpl ?? globalThis.fetch
  const auth = options.auth ?? true

  const send = async (token: string | undefined): Promise<Response> => {
    const headers: Record<string, string> = {
      accept: 'application/json',
      ...options.headers,
    }
    if (options.body !== undefined) {
      headers['content-type'] = 'application/json'
    }
    if (auth && token) {
      headers['authorization'] = `Bearer ${token}`
    }
    try {
      return await fetchImpl(`${baseUrl}${path}`, {
        method: options.method ?? 'GET',
        headers,
        body:
          options.body === undefined
            ? undefined
            : JSON.stringify(options.body),
      })
    } catch {
      throw new NetworkError()
    }
  }

  let response: Response
  try {
    response = await send(options.cookies.get(ACCESS_COOKIE))
  } catch {
    // The API is unreachable: report it, never throw across the boundary.
    return { ok: false, code: NETWORK_ERROR, status: 0 }
  }

  if (response.status === 401 && auth) {
    const refreshed = await refreshAccessToken(
      options.cookies,
      fetchImpl,
      baseUrl,
    )
    if (!refreshed.ok) {
      return { ok: false, code: refreshed.code, status: refreshed.status }
    }
    // Exactly one retry with the new access token.
    try {
      response = await send(refreshed.token)
    } catch {
      return { ok: false, code: NETWORK_ERROR, status: 0 }
    }
  }

  return readResult<T>(response)
}
