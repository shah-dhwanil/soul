import { createFileRoute } from '@tanstack/react-router'
import { Button } from '~/components/ui/button'

export const Route = createFileRoute('/')({
  component: () => (
    <div className="mx-auto w-full max-w-5xl px-6 py-24">
      <h1 className="font-display text-4xl">A friend who pays attention.</h1>
      <p className="mt-4 max-w-prose text-[var(--wren-ink-muted)]">
        Wren is an AI that remembers what you tell it and says what it actually
        thinks. This page is a placeholder while the real one is built.
      </p>
      <Button className="mt-8 rounded-full px-6">Begin</Button>
    </div>
  ),
})
