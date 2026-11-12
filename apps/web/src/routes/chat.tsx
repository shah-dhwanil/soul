import { createFileRoute, redirect } from '@tanstack/react-router'
import { useState } from 'react'
import { Composer } from '~/components/chat/Composer'
import { MessageList } from '~/components/chat/MessageList'
import { TypingIndicator } from '~/components/chat/TypingIndicator'
import { Button } from '~/components/ui/button'
import { appendTurn, type TranscriptItem } from '~/lib/chat'
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
  const [items, setItems] = useState<TranscriptItem[]>(() => [
    { id: 'opener', type: 'message', role: 'wren', text: firstLine },
  ])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [failed, setFailed] = useState<string | null>(null)

  async function send(text: string) {
    setPending(true)
    setError(null)
    const result = await sendChat({ data: { message: text } })
    setPending(false)
    if (!result.ok) {
      // The message stays in the transcript so nothing the user wrote is lost.
      setItems((current) => [
        ...current,
        {
          id: `user-${current.length}`,
          type: 'message',
          role: 'user',
          text,
        },
      ])
      setFailed(text)
      setError(
        result.code === 'rate_limited'
          ? 'Too many messages at once. Give it a moment.'
          : 'That message did not go through. Try again.',
      )
      return
    }
    setFailed(null)
    setItems((current) => appendTurn(current, text, result.data))
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
    setItems([
      {
        id: `opener-${result.data.conversationId}`,
        type: 'message',
        role: 'wren',
        text: result.data.firstMessage,
      },
    ])
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

      <MessageList items={items} />

      {pending ? (
        <div className="wren-card w-fit rounded-bl-md">
          <TypingIndicator />
        </div>
      ) : null}

      {error ? (
        <div role="alert" className="flex items-center gap-4 text-sm text-[#a2442c]">
          <span>{error}</span>
          {failed ? (
            <button
              type="button"
              className="rounded-full border border-[var(--wren-border)] px-3 py-1 text-[var(--wren-ink)]"
              onClick={() => send(failed)}
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
