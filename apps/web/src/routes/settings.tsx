import { createFileRoute, redirect } from '@tanstack/react-router'
import { sessionGuard } from '~/server/session-guard'

export const Route = createFileRoute('/settings')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  component: () => (
    <div className="mx-auto w-full max-w-2xl px-6 py-24">
      <h1 className="font-display text-3xl">Settings</h1>
      <p className="mt-3 text-[var(--wren-ink-muted)]">
        The dials are being tuned. This page is a placeholder.
      </p>
    </div>
  ),
})
