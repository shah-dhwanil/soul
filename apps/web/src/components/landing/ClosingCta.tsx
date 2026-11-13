import { Link } from '@tanstack/react-router'
import { useRef } from 'react'
import { useReveal } from '~/lib/motion'

export function ClosingCta() {
  const ref = useRef<HTMLElement>(null)
  useReveal(ref)

  return (
    <section ref={ref} className="mx-auto w-full max-w-5xl px-6 py-20 sm:py-28">
      <div className="wren-card flex flex-col items-start gap-6 p-10 sm:p-14">
        <h2 data-reveal className="font-display max-w-lg text-3xl sm:text-4xl">
          Start talking. Wren will pick it up from there.
        </h2>
        <Link
          data-reveal
          to="/onboarding"
          className="rounded-full bg-[var(--wren-accent)] px-7 py-3 text-[var(--wren-ink)] transition-transform hover:-translate-y-0.5"
        >
          Begin
        </Link>
      </div>
    </section>
  )
}

export function Footer() {
  return (
    <footer className="border-t border-[var(--wren-border)]">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 px-6 py-10 text-sm text-[var(--wren-ink-muted)] sm:flex-row sm:items-center sm:justify-between">
        <p>Wren — a friend who pays attention.</p>
        <nav className="flex items-center gap-6">
          <a href="/privacy" className="underline-offset-4 hover:underline">
            Privacy
          </a>
          <a href="/terms" className="underline-offset-4 hover:underline">
            Terms
          </a>
        </nav>
      </div>
    </footer>
  )
}
