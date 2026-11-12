import type {
  AdviceMode,
  CheckInMode,
  EmojiMode,
  LengthBand,
  Settings,
  SettingsPatch,
} from '~/lib/types'

/**
 * The settings a person can change, as one flat object.
 *
 * The API stores three views (explicit, learned, effective); the page edits
 * one flat set of values and writes back only what changed.
 */

export interface SettingsValues {
  warmth: number
  directness: number
  humor: number
  initiative: number
  length: LengthBand
  advice: AdviceMode
  checkIns: CheckInMode
  emoji: EmojiMode
  address: string
  nickname: string
}

/** What a dial falls back to when nothing is set. */
export const DIAL_DEFAULTS = {
  warmth: 7,
  directness: 6,
  humor: 4,
  initiative: 3,
} as const

export const PREFERENCE_DEFAULTS = {
  length: 'match',
  advice: 'ask_first',
  checkIns: 'off',
  emoji: 'never',
} as const satisfies {
  length: LengthBand
  advice: AdviceMode
  checkIns: CheckInMode
  emoji: EmojiMode
}

function numberOf(
  source: Record<string, unknown>,
  key: string,
  fallback: number,
): number {
  const value = source[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function stringOf(
  source: Record<string, unknown>,
  key: string,
  fallback: string,
): string {
  const value = source[key]
  return typeof value === 'string' ? value : fallback
}

/** The editable values, read from the effective view. */
export function valuesFromSettings(settings: Settings | null): SettingsValues {
  const effective = settings?.effective ?? {}
  return {
    warmth: numberOf(effective, 'warmth', DIAL_DEFAULTS.warmth),
    directness: numberOf(effective, 'directness', DIAL_DEFAULTS.directness),
    humor: numberOf(effective, 'humor', DIAL_DEFAULTS.humor),
    initiative: numberOf(effective, 'initiative', DIAL_DEFAULTS.initiative),
    length: stringOf(
      effective,
      'length',
      PREFERENCE_DEFAULTS.length,
    ) as LengthBand,
    advice: stringOf(
      effective,
      'advice',
      PREFERENCE_DEFAULTS.advice,
    ) as AdviceMode,
    checkIns: stringOf(
      effective,
      'check_ins',
      PREFERENCE_DEFAULTS.checkIns,
    ) as CheckInMode,
    emoji: stringOf(
      effective,
      'emoji',
      PREFERENCE_DEFAULTS.emoji,
    ) as EmojiMode,
    address: stringOf(effective, 'address', ''),
    nickname: stringOf(effective, 'nickname', ''),
  }
}

/** True when this dial has never been set by hand: it is the temperament's. */
export function isTemperamentDefault(
  settings: Settings | null,
  dial: 'warmth' | 'directness' | 'humor' | 'initiative',
): boolean {
  const explicit = settings?.explicit ?? {}
  return explicit[dial] === undefined
}

/** Only what changed, so a save never rewrites the rest. */
export function patchFromValues(
  next: SettingsValues,
  previous: SettingsValues,
): SettingsPatch {
  const patch: SettingsPatch = {}
  if (next.warmth !== previous.warmth) patch.warmth = next.warmth
  if (next.directness !== previous.directness) patch.directness = next.directness
  if (next.humor !== previous.humor) patch.humor = next.humor
  if (next.initiative !== previous.initiative) patch.initiative = next.initiative
  if (next.length !== previous.length) patch.length = next.length
  if (next.advice !== previous.advice) patch.advice = next.advice
  if (next.checkIns !== previous.checkIns) patch.checkIns = next.checkIns
  if (next.emoji !== previous.emoji) patch.emoji = next.emoji
  if (next.address !== previous.address) patch.address = next.address
  if (next.nickname !== previous.nickname) patch.nickname = next.nickname
  return patch
}
