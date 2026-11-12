import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Textarea } from '~/components/ui/textarea'
import { canSend } from '~/lib/chat'

/**
 * The composer. A message that is blank or only whitespace cannot be sent.
 */
export function Composer({
  pending,
  onSend,
}: {
  pending: boolean
  onSend: (text: string) => void
}) {
  const [text, setText] = useState('')
  const ready = canSend(text) && !pending

  function send() {
    if (!ready) return
    const value = text.trim()
    setText('')
    onSend(value)
  }

  return (
    <div className="flex items-end gap-3">
      <Textarea
        aria-label="Message Wren"
        placeholder="Say something…"
        rows={1}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            send()
          }
        }}
        className="min-h-12 resize-none rounded-3xl bg-[var(--wren-surface)]"
      />
      <Button
        type="button"
        onClick={send}
        disabled={!ready}
        className="rounded-full px-6"
      >
        {pending ? 'Sending…' : 'Send'}
      </Button>
    </div>
  )
}
