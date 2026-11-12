import type { ChatResult } from '~/lib/types'

/**
 * The chat transcript.
 *
 * Every item is either something Wren said, something the user said, a
 * divider, or a notice. User text is only ever rendered as text.
 */

export type TranscriptItem =
  | { id: string; type: 'message'; role: 'wren' | 'user'; text: string }
  | { id: string; type: 'divider'; label: string }
  | { id: string; type: 'notice'; notice: 'memory-degraded'; text: string }

/** A message may only be sent when it says something. */
export function canSend(text: string): boolean {
  return text.trim().length > 0
}

/**
 * Add one exchange to the transcript.
 *
 * A `new_thread` reply gets a divider above it; a `memoryDegraded` reply
 * gets one notice under it.
 */
export function appendTurn(
  items: TranscriptItem[],
  userText: string,
  result: ChatResult,
): TranscriptItem[] {
  const base = items.length
  const next: TranscriptItem[] = [...items]

  next.push({
    id: `user-${base}`,
    type: 'message',
    role: 'user',
    text: userText,
  })
  if (result.newThread) {
    next.push({
      id: `divider-${base}`,
      type: 'divider',
      label: 'New conversation',
    })
  }
  next.push({
    id: `wren-${base}`,
    type: 'message',
    role: 'wren',
    text: result.reply,
  })
  if (result.memoryDegraded) {
    next.push({
      id: `notice-${base}`,
      type: 'notice',
      notice: 'memory-degraded',
      text: 'Wren is having trouble remembering right now, so this reply may be missing some context.',
    })
  }

  return next
}
