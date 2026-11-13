import type {
  ApiAuthUser,
  ApiChatResponse,
  ApiConversationCreated,
  ApiLeaning,
  ApiSettings,
  ApiTemperament,
  ApiTrait,
  ApiUserSummary,
  AuthUser,
  ChatResult,
  Conversation,
  Leaning,
  Settings,
  SettingValue,
  Temperament,
  Trait,
  UserSummary,
  YouView,
} from '~/lib/types'

/**
 * The one place the API's snake_case becomes the web client's camelCase.
 */

export function toAuthUser(api: ApiAuthUser): AuthUser {
  return {
    userId: api.user_id,
    email: api.email,
    onboarded: api.onboarded,
    onboardingStep: api.onboarding_step,
  }
}

export function toTemperament(api: ApiTemperament): Temperament {
  return {
    id: api.id,
    feelsLike: api.feels_like,
    humor: api.humor,
    curiosity: api.curiosity,
    pushback: api.pushback,
    pace: api.pace,
    firstLine: api.first_line,
    sampleReply: api.sample_reply,
  }
}

export function toTemperaments(api: {
  temperaments: ApiTemperament[]
}): Temperament[] {
  return api.temperaments.map(toTemperament)
}

/**
 * Settings values are flat primitives; anything else is dropped rather than
 * carried into the browser.
 */
export function toSettingMap(
  input: Record<string, unknown>,
): Record<string, SettingValue> {
  const out: Record<string, SettingValue> = {}
  for (const [key, value] of Object.entries(input ?? {})) {
    if (
      value === null ||
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    ) {
      out[key] = value
    }
  }
  return out
}

export function toSettings(api: ApiSettings): Settings {
  return {
    explicit: toSettingMap(api.explicit),
    learned: toSettingMap(api.learned),
    effective: toSettingMap(api.effective),
  }
}

export function toTrait(api: ApiTrait): Trait {
  return {
    id: api.id,
    kind: api.kind,
    label: api.label,
    status: api.status,
    lastLanded: api.last_landed ?? null,
  }
}

export function toLeaning(api: ApiLeaning): Leaning {
  return {
    id: api.id,
    kind: api.kind,
    value: api.value,
    status: api.status,
  }
}

export function toYouView(
  traits: ApiTrait[],
  leanings: ApiLeaning[],
  facts: string[],
): YouView {
  return {
    traits: traits.map(toTrait),
    leanings: leanings.map(toLeaning),
    facts,
  }
}

/** `mode`, `concern_tier` and `decisions` are dropped here on purpose. */
export function toChatResult(api: ApiChatResponse): ChatResult {
  return {
    threadId: api.thread_id,
    turnId: api.turn_id,
    reply: api.reply,
    newThread: api.new_thread,
    memoryDegraded: api.memory_degraded,
  }
}

export function toUserSummary(api: ApiUserSummary): UserSummary {
  return {
    temperament: api.temperament,
    locale: api.locale,
    stagePermissions: api.stage_permissions,
    dialsWords: api.dials_words,
    traitsCount: api.traits_count,
    leanings: api.leanings.map(toLeaning),
  }
}

export function toConversation(api: ApiConversationCreated): Conversation {
  return {
    conversationId: api.conversation_id,
    firstMessage: api.first_message,
  }
}
