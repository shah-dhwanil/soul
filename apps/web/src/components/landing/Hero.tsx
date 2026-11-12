import { Link } from '@tanstack/react-router'
import { useRef } from 'react'
import { useEntrance } from '~/lib/motion'

/**
 * The first thing anyone sees.
 */
export function Hero() {
  const ref = useRef<HTMLElement>(null)
  useEntrance(ref)

  return (
    <section ref={ref} className="relative overflow-hidden">
      <div
        aria-hidden
        className="wren-blob pointer-events-none absolute -right-24 -top-24 h-80 w-80 bg-[var(--wren-accent-soft)] opacity-70"
      />
      <div
        aria-hidden
        className="wren-blob-alt pointer-events-none absolute -left-32 top-40 h-64 w-64 bg-[var(--wren-accent)] opacity-15"
      />

      <div className="relative mx-auto w-full max-w-5xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-28">
        <p
          data-reveal
          className="text-sm uppercase tracking-[0.2em] text-[var(--wren-ink-muted)]"
        >
          Wren
        </p>
        <h1
          data-reveal
          className="font-display mt-4 max-w-2xl text-5xl leading-[1.05] sm:text-6xl"
        >
          A friend who pays attention.
        </h1>
        <p
          data-reveal
          className="mt-6 max-w-xl text-lg leading-relaxed text-[var(--wren-ink-muted)]"
        >
          A steady friend who pays attention, tells you the truth once, and
          becomes recognizably yours the longer you talk.
        </p>
        <div data-reveal className="mt-10 flex flex-wrap items-center gap-4">
          <Link
            to="/onboarding"
            className="rounded-full bg-[var(--wren-accent)] px-7 py-3 text-[var(--wren-ink)] transition-transform hover:-translate-y-0.5"
          >
            Begin
          </Link>
          <Link
            to="/login"
            className="rounded-full border border-[var(--wren-border)] px-7 py-3 underline-offset-4 hover:underline"
          >
            Sign in
          </Link>
        </div>
      </div>
    </section>
  )
}
