import { createServerFn } from '@tanstack/react-start'
import type {
  ApiAuthUser,
  ApiChatResponse,
  ApiConversationCreated,
  ApiLeaning,
  ApiSettings,
  ApiTemperament,
  ApiTrait,
  ApiUserSummary,
  ChatResult,
  Conversation,
  Result,
  Settings,
  SettingsPatch,
  Temperament,
  UserSummary,
  YouView,
} from '~/lib/types'
import { callApi } from './client'
import {
  toChatResult,
  toConversation,
  toLeaning,
  toSettings,
  toTemperaments,
  toTrait,
  toUserSummary,
  toYouView,
} from './mappers'
import { createServerCookieJar } from './server-cookies'
import type { CookieJar } from './session'

/**
 * Everything Wren's own API needs: the temperaments, the persona, the
 * settings, the conversation, and what Wren has noticed.
 */

/** The signed-in account's id, or a failure. */
async function requireUserId(
  cookies: CookieJar,
): Promise<Result<{ userId: string }>> {
  const result = await callApi<ApiAuthUser>('/v1/auth/me', { cookies })
  if (!result.ok) {
    return { ok: false, code: result.code, status: result.status }
  }
  return { ok: true, data: { userId: result.data.user_id } }
}

/** The four seeds. Public: no session needed. */
export const temperaments = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Result<Temperament[]>> => {
    const cookies = createServerCookieJar()
    const result = await callApi<{ temperaments: ApiTemperament[] }>(
      '/v1/onboarding/temperaments',
      { cookies, auth: false },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toTemperaments(result.data) }
  },
)

/** Create the persona with a temperament. Idempotent on the server. */
export const createUser = createServerFn({ method: 'POST' })
  .validator((data: { temperamentId: string }) => data)
  .handler(async ({ data }): Promise<Result<{ temperament: string }>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<{ temperament: string }>('/v1/users', {
      cookies,
      method: 'POST',
      body: {
        temperament: data.temperamentId,
        locale: 'en-US',
        timezone: 'UTC',
      },
    })
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: { temperament: result.data.temperament } }
  })

/** Change the temperament of an existing persona, re-seeding it. */
export const changeTemperament = createServerFn({ method: 'POST' })
  .validator((data: { temperamentId: string }) => data)
  .handler(async ({ data }): Promise<Result<{ temperament: string }>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<{ temperament: string }>(
      `/v1/users/${user.data.userId}/temperament`,
      { cookies, method: 'PATCH', body: { temperament: data.temperamentId } },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: { temperament: result.data.temperament } }
  })

/** The persona summary for the signed-in account. */
export const fetchUserSummary = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Result<UserSummary>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<ApiUserSummary>(
      `/v1/users/${user.data.userId}`,
      { cookies },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toUserSummary(result.data) }
  },
)

/** The settings view: explicit, learned, effective. */
export const fetchSettings = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Result<Settings>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<ApiSettings>(
      `/v1/users/${user.data.userId}/settings`,
      { cookies },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toSettings(result.data) }
  },
)

/** Write part of the settings. */
export const patchSettings = createServerFn({ method: 'POST' })
  .validator((data: SettingsPatch) => data)
  .handler(async ({ data }): Promise<Result<Settings>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const body: Record<string, unknown> = {}
    if (data.warmth !== undefined) body.warmth = data.warmth
    if (data.directness !== undefined) body.directness = data.directness
    if (data.humor !== undefined) body.humor = data.humor
    if (data.initiative !== undefined) body.initiative = data.initiative
    if (data.length !== undefined) body.length = data.length
    if (data.advice !== undefined) body.advice = data.advice
    if (data.checkIns !== undefined) body.check_ins = data.checkIns
    if (data.emoji !== undefined) body.emoji = data.emoji
    if (data.address !== undefined) body.address = data.address
    if (data.nickname !== undefined) body.nickname = data.nickname

    const result = await callApi<ApiSettings>(
      `/v1/users/${user.data.userId}/settings`,
      { cookies, method: 'PATCH', body },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toSettings(result.data) }
  })

/** Forget everything Wren learned, keeping what you set by hand. */
export const resetLearned = createServerFn({ method: 'POST' }).handler(
  async (): Promise<Result<Settings>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<ApiSettings>(
      `/v1/users/${user.data.userId}/settings/reset-learned`,
      { cookies, method: 'POST' },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toSettings(result.data) }
  },
)

/** Send one message and get Wren's reply. */
export const sendChat = createServerFn({ method: 'POST' })
  .validator((data: { message: string }) => data)
  .handler(async ({ data }): Promise<Result<ChatResult>> => {
    const cookies = createServerCookieJar()
    const result = await callApi<ApiChatResponse>('/v1/chat', {
      cookies,
      method: 'POST',
      body: { message: data.message },
    })
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toChatResult(result.data) }
  })

/** Start a new conversation; Wren opens with its first line. */
export const startConversation = createServerFn({ method: 'POST' }).handler(
  async (): Promise<Result<Conversation>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const result = await callApi<ApiConversationCreated>(
      `/v1/users/${user.data.userId}/conversations`,
      { cookies, method: 'POST' },
    )
    if (!result.ok) {
      return { ok: false, code: result.code, status: result.status }
    }
    return { ok: true, data: toConversation(result.data) }
  })

/** What Wren has noticed: traits, leanings, and memory facts. */
export const fetchYou = createServerFn({ method: 'GET' }).handler(
  async (): Promise<Result<YouView>> => {
    const cookies = createServerCookieJar()
    const user = await requireUserId(cookies)
    if (!user.ok) return user
    const [traitsResult, memoryResult] = await Promise.all([
      callApi<{ traits: ApiTrait[]; leanings: ApiLeaning[] }>(
        `/v1/users/${user.data.userId}/traits`,
        { cookies },
      ),
      callApi<{ facts: string[] }>(`/v1/users/${user.data.userId}/memory`, {
        cookies,
      }),
    ])
    if (!traitsResult.ok) {
      return { ok: false, code: traitsResult.code, status: traitsResult.status }
    }
    if (!memoryResult.ok) {
      return { ok: false, code: memoryResult.code, status: memoryResult.status }
    }
    return {
      ok: true,
      data: toYouView(
        traitsResult.data.traits,
        traitsResult.data.leanings,
        memoryResult.data.facts,
      ),
    }
  },
)
