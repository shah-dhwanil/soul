import { createFileRoute, redirect } from '@tanstack/react-router'
import { sessionGuard } from '~/server/session-guard'

export const Route = createFileRoute('/chat')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  component: () => (
    <div className="mx-auto w-full max-w-2xl px-6 py-24">
      <h1 className="font-display text-3xl">Chat</h1>
      <p className="mt-3 text-[var(--wren-ink-muted)]">
        The conversation is being built. This page is a placeholder.
      </p>
    </div>
  ),
})
