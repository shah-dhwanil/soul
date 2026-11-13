import { useRef } from 'react'
import { useReveal } from '~/lib/motion'

/**
 * The four temperaments, described the way Wren describes itself.
 * The copy here is fixed text — the real seeds come from the API.
 */
const TEMPERAMENTS = [
  {
    id: 'steady',
    name: 'Steady',
    feelsLike: 'Even, dry, observant',
    line: 'Productive avoidance. What’s the report actually asking for?',
  },
  {
    id: 'wry',
    name: 'Wry',
    feelsLike: 'Quick, playful, deadpan',
    line: 'Clean desk, empty document. The classic trade. What’s the report about?',
  },
  {
    id: 'gentle',
    name: 'Gentle',
    feelsLike: 'Slow, soft, patient',
    line: 'A clean desk is still a small win. What’s the report holding?',
  },
  {
    id: 'tinker',
    name: 'Tinker',
    feelsLike: 'Curious, practical, makes things smaller',
    line: 'What’s the first piece you could finish in ten minutes?',
  },
]

export function TemperamentTeaser() {
  const ref = useRef<HTMLElement>(null)
  useReveal(ref, { stagger: 0.1 })

  return (
    <section ref={ref} className="mx-auto w-full max-w-5xl px-6 py-20 sm:py-28">
      <div className="max-w-2xl">
        <h2 data-reveal className="font-display text-3xl sm:text-4xl">
          Four ways of being.
        </h2>
        <p data-reveal className="mt-4 leading-relaxed text-[var(--wren-ink-muted)]">
          Wren starts with one temperament, and it does not change to please
          you. You pick it once; the rest is what the two of you build.
        </p>
      </div>

      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {TEMPERAMENTS.map((temperament) => (
          <article
            key={temperament.id}
            data-reveal
            className="wren-card flex flex-col gap-3 p-6"
          >
            <h3 className="font-display text-xl">{temperament.name}</h3>
            <p className="text-sm text-[var(--wren-ink-muted)]">
              {temperament.feelsLike}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-[var(--wren-ink)]">
              “{temperament.line}”
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}
