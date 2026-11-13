import { useRef } from 'react'
import { useReveal } from '~/lib/motion'

const STATEMENTS = [
  {
    title: 'It remembers. On purpose.',
    body: 'Wren keeps what you tell it — your name, what you care about, the thing you said last week. You do not have to start over every morning.',
  },
  {
    title: 'It tells you the truth once.',
    body: 'No flattery, no cheerleading, no endless agreeing. If Wren disagrees, it says so once, plainly, with a reason.',
  },
  {
    title: 'It becomes yours.',
    body: 'Shared words, jokes, and rhythms accumulate. After a while, the conversation is recognizably yours and nobody else’s.',
  },
]

export function WhatIs() {
  const ref = useRef<HTMLElement>(null)
  useReveal(ref)

  return (
    <section ref={ref} className="mx-auto w-full max-w-5xl px-6 py-20 sm:py-28">
      <div className="grid gap-10 sm:grid-cols-3">
        {STATEMENTS.map((statement) => (
          <div key={statement.title} data-reveal>
            <h2 className="font-display text-2xl">{statement.title}</h2>
            <p className="mt-3 leading-relaxed text-[var(--wren-ink-muted)]">
              {statement.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
