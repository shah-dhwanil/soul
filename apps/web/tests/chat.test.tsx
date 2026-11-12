import { describe, expect, test, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Composer } from '~/components/chat/Composer'
import { MessageList } from '~/components/chat/MessageList'
import { appendTurn, canSend, type TranscriptItem } from '~/lib/chat'

const reply = {
  threadId: 'th1',
  turnId: 'tu1',
  reply: 'Noted.',
  newThread: false,
  memoryDegraded: false,
}

describe('chat', () => {
  test('blank_message_blocked', () => {
    const onSend = vi.fn()
    render(<Composer pending={false} onSend={onSend} />)

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toHaveProperty('disabled', true)

    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '   ' } })

    expect(screen.getByRole('button', { name: /send/i })).toHaveProperty(
      'disabled',
      true,
    )
    fireEvent.keyDown(textarea, { key: 'Enter' })
    expect(onSend).not.toHaveBeenCalled()
  })

  test('new_thread_inserts_divider', () => {
    const items: TranscriptItem[] = [
      { id: '1', type: 'message', role: 'user', text: 'hello' },
      { id: '2', type: 'divider', label: 'New conversation' },
      { id: '3', type: 'message', role: 'wren', text: 'hello again' },
    ]
    const { container } = render(<MessageList items={items} />)

    const divider = container.querySelector('[data-testid="divider"]')
    expect(divider).not.toBeNull()
    expect(divider?.textContent).toContain('New conversation')

    const nodes = [...container.querySelectorAll('[data-testid]')]
    const dividerIndex = nodes.findIndex(
      (element) => element.getAttribute('data-testid') === 'divider',
    )
    const replyIndex = nodes.findIndex(
      (element) =>
        element.getAttribute('data-testid') === 'bubble' &&
        element.getAttribute('data-role') === 'wren',
    )
    expect(dividerIndex).toBeGreaterThanOrEqual(0)
    expect(dividerIndex).toBeLessThan(replyIndex)
  })

  test('memory_degraded_shows_notice', () => {
    const items = appendTurn([], 'hello', {
      ...reply,
      memoryDegraded: true,
    })
    const { container } = render(<MessageList items={items} />)

    expect(container.querySelectorAll('[data-testid="notice"]')).toHaveLength(1)
    expect(screen.getByText(/remembering/i)).toBeTruthy()
    expect(screen.getByText('Noted.')).toBeTruthy()
  })

  test('renders_reply_as_text', () => {
    const items = appendTurn([], 'hello', {
      ...reply,
      reply: '<img src=x onerror=alert(1)>',
    })
    const { container } = render(<MessageList items={items} />)

    expect(container.querySelector('img')).toBeNull()
    expect(container.innerHTML).toContain('&lt;img src=x onerror=alert(1)&gt;')
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy()
  })

  test('can_send_ignores_whitespace', () => {
    expect(canSend('   ')).toBe(false)
    expect(canSend('')).toBe(false)
    expect(canSend('hi')).toBe(true)
  })
})
