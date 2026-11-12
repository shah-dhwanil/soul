/**
 * The shapes the web client speaks.
 *
 * The browser never sees the API's snake_case bodies: `src/server/*` maps
 * them to the camelCase types below, once, here. Raw API payloads live at
 * the bottom of this file and never leave the server layer.
 */

/** Every server function returns this instead of throwing. */
export type Result<T> =
  | { ok: true; data: T }
  | { ok: false; code: string; status: number }

/** The token pair the API hands back on register and login. */
export interface Tokens {
  accessToken: string
  refreshToken: string
}

/** The signed-in account. `onboardingStep` is the server-side resume pointer. */
export interface AuthUser {
  userId: string
  email: string
  onboarded: boolean
  onboardingStep: number
}

/** One temperament seed from `GET /v1/onboarding/temperaments`. */
export interface Temperament {
  id: string
  feelsLike: string
  humor: string
  curiosity: string
  pushback: string
  pace: string
  firstLine: string
  sampleReply: string
}

/** The four dials, with the ranges the API enforces. */
export interface Dials {
  warmth: number
  directness: number
  humor: number
  initiative: number
}

/** Reply length band. */
export type LengthBand = 'brief' | 'match' | 'longer'
/** How eagerly Wren offers advice. */
export type AdviceMode = 'ask_first' | 'once' | 'direct'
/** How often Wren checks in unprompted. */
export type CheckInMode = 'off' | 'events' | 'occasional'
/** Emoji use. */
export type EmojiMode = 'never' | 'only_if_i_use_them'

/** A value a setting can hold. */
export type SettingValue = string | number | boolean | null

/** The settings view: what was set explicitly, what was learned, what applies. */
export interface Settings {
  explicit: Record<string, SettingValue>
  learned: Record<string, SettingValue>
  effective: Record<string, SettingValue>
}

/** The settable slice of settings. `checkIns` maps to the API's `check_ins`. */
export interface SettingsPatch {
  warmth?: number
  directness?: number
  humor?: number
  initiative?: number
  length?: LengthBand
  advice?: AdviceMode
  checkIns?: CheckInMode
  emoji?: EmojiMode
  address?: string
  nickname?: string
}

/** A piece of shared language Wren may use because the user started it. */
export interface Trait {
  id: string
  kind: string
  label: string
  status: string
  lastLanded: string | null
}

/** A way Wren acts, learned from the user's reactions. */
export interface Leaning {
  id: string
  kind: string
  value: string
  status: string
}

/** What Wren has noticed so far. Read-only. */
export interface YouView {
  traits: Trait[]
  leanings: Leaning[]
  facts: string[]
}

/**
 * One chat turn. `mode`, `concern_tier` and `decisions` are deliberately
 * absent: they are internal to Wren and never rendered.
 */
export interface ChatResult {
  threadId: string
  turnId: string
  reply: string
  newThread: boolean
  memoryDegraded: boolean
}

/** The persona summary for the signed-in account. */
export interface UserSummary {
  temperament: string
  locale: string
  stagePermissions: string
  dialsWords: string
  traitsCount: number
  leanings: Leaning[]
}

/** A newly started conversation and the line Wren opens with. */
export interface Conversation {
  conversationId: string
  firstMessage: string
}

/* ------------------------------------------------------------------ */
/* Raw API payloads (server layer only).                              */
/* ------------------------------------------------------------------ */

export interface ApiAuthUser {
  user_id: string
  email: string
  onboarded: boolean
  onboarding_step: number
  access_token?: string
  refresh_token?: string
}

export interface ApiTemperament {
  id: string
  feels_like: string
  humor: string
  curiosity: string
  pushback: string
  pace: string
  first_line: string
  sample_reply: string
}

export interface ApiSettings {
  explicit: Record<string, unknown>
  learned: Record<string, unknown>
  effective: Record<string, unknown>
}

export interface ApiUserSummary {
  temperament: string
  locale: string
  stage_permissions: string
  dials_words: string
  traits_count: number
  leanings: ApiLeaning[]
}

export interface ApiTrait {
  id: string
  kind: string
  label: string
  status: string
  last_landed: string | null
}

export interface ApiLeaning {
  id: string
  kind: string
  value: string
  status: string
}

export interface ApiChatResponse {
  thread_id: string
  turn_id: string
  conversation_id: string | null
  reply: string
  new_thread: boolean
  memory_degraded: boolean
  decisions: Record<string, unknown>
  mode: string | null
  concern_tier: string | null
}

export interface ApiConversationCreated {
  conversation_id: string
  first_message: string
}
