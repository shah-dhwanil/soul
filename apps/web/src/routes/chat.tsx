import { createFileRoute, redirect } from '@tanstack/react-router'
import { useState } from 'react'
import { Composer } from '~/components/chat/Composer'
import { MessageList } from '~/components/chat/MessageList'
import { TypingIndicator } from '~/components/chat/TypingIndicator'
import { Button } from '~/components/ui/button'
import {
  appendReply,
  appendUserMessage,
  type ChatState,
} from '~/lib/chat'
import { sessionGuard } from '~/server/session-guard'
import {
  fetchUserSummary,
  sendChat,
  startConversation,
  temperaments,
} from '~/server/wren'

export const Route = createFileRoute('/chat')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  loader: async () => {
    const [summaryResult, temperamentsResult] = await Promise.all([
      fetchUserSummary(),
      temperaments(),
    ])
    const summary = summaryResult.ok ? summaryResult.data : null
    const seeds = temperamentsResult.ok ? temperamentsResult.data : []
    const seed = seeds.find((item) => item.id === summary?.temperament)
    return {
      firstLine: seed?.firstLine ?? 'Hi. I’m Wren.',
      temperament: summary?.temperament ?? null,
    }
  },
  component: ChatPage,
})

function ChatPage() {
  const { firstLine } = Route.useLoaderData()
  const [state, setState] = useState<ChatState>(() => ({
    items: [{ id: 'opener', type: 'message', role: 'wren', text: firstLine }],
    failedText: null,
  }))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send(text: string, isRetry = false) {
    if (!isRetry) {
      // The message goes into the transcript once, whether it works or not.
      setState((current) => ({
        ...current,
        items: appendUserMessage(current.items, text),
      }))
    }
    setPending(true)
    setError(null)
    const result = await sendChat({ data: { message: text } })
    setPending(false)
    if (!result.ok) {
      setState((current) => ({ ...current, failedText: text }))
      setError(
        result.code === 'rate_limited'
          ? 'Too many messages at once. Give it a moment.'
          : 'That message did not go through. Try again.',
      )
      return
    }
    setState((current) => ({
      ...current,
      items: appendReply(current.items, result.data),
      failedText: null,
    }))
  }

  async function newConversation() {
    setPending(true)
    setError(null)
    const result = await startConversation()
    setPending(false)
    if (!result.ok) {
      setError('A new conversation did not start. Try again.')
      return
    }
    setState({
      items: [
        {
          id: `opener-${result.data.conversationId}`,
          type: 'message',
          role: 'wren',
          text: result.data.firstMessage,
        },
      ],
      failedText: null,
    })
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl">Wren</h1>
        <Button
          type="button"
          variant="outline"
          onClick={newConversation}
          disabled={pending}
          className="rounded-full"
        >
          New conversation
        </Button>
      </div>

      <MessageList items={state.items} />

      {pending ? (
        <div className="wren-card w-fit rounded-bl-md">
          <TypingIndicator />
        </div>
      ) : null}

      {error ? (
        <div role="alert" className="flex items-center gap-4 text-sm text-[#a2442c]">
          <span>{error}</span>
          {state.failedText ? (
            <button
              type="button"
              className="rounded-full border border-[var(--wren-border)] px-3 py-1 text-[var(--wren-ink)]"
              onClick={() => send(state.failedText as string, true)}
            >
              Try again
            </button>
          ) : null}
        </div>
      ) : null}

      <Composer pending={pending} onSend={send} />
    </div>
  )
}
