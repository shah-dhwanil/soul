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
  return appendReply(appendUserMessage(items, userText), result)
}

/** The user's own message, added once. */
export function appendUserMessage(
  items: TranscriptItem[],
  text: string,
): TranscriptItem[] {
  return [
    ...items,
    {
      id: `user-${items.length}`,
      type: 'message',
      role: 'user',
      text,
    },
  ]
}

/** Wren's reply, with its divider and its notice. */
export function appendReply(
  items: TranscriptItem[],
  result: ChatResult,
): TranscriptItem[] {
  const base = items.length
  const next: TranscriptItem[] = [...items]

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

/** The chat transcript and what failed last. */
export interface ChatState {
  items: TranscriptItem[]
  /** The message that did not go through, kept so it can be retried. */
  failedText: string | null
}

export type ChatAction =
  | { type: 'user-message'; text: string }
  | { type: 'failed'; text: string }
  | { type: 'reply'; result: ChatResult }
  | { type: 'reset'; text: string }

/**
 * The transcript reducer.
 *
 * A retry sends the message again without adding a second copy of it to the
 * transcript: the user's message appears exactly once.
 */
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'user-message':
      return {
        items: appendUserMessage(state.items, action.text),
        failedText: null,
      }
    case 'failed':
      return { ...state, failedText: action.text }
    case 'reply':
      return {
        items: appendReply(state.items, action.result),
        failedText: null,
      }
    case 'reset':
      return {
        items: [
          {
            id: `opener-${action.text}`,
            type: 'message',
            role: 'wren',
            text: action.text,
          },
        ],
        failedText: null,
      }
    default:
      return state
  }
}

/**
 * The Wren bubbles that have not been revealed yet.
 *
 * Only new bubbles animate: the history must not blink every time Wren
 * replies. The bubbles handed out are marked, so they never animate twice.
 */
export function unanimatedWrenBubbles(root: ParentNode): Element[] {
  const bubbles = Array.from(
    root.querySelectorAll('[data-role="wren"]:not([data-animated])'),
  )
  for (const bubble of bubbles) {
    bubble.setAttribute('data-animated', 'true')
  }
  return bubbles
}
