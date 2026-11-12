import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Slider } from '~/components/ui/slider'
import type { Dials } from '~/lib/types'

/** The API enforces these ranges; the UI cannot offer anything else. */
export const DIAL_RANGES = {
  warmth: { min: 5, max: 8, label: 'Warmth', hint: 'How soft the edges are.' },
  directness: {
    min: 4,
    max: 8,
    label: 'Directness',
    hint: 'How plainly I say the thing.',
  },
  humor: { min: 0, max: 6, label: 'Humor', hint: 'How often I joke.' },
  initiative: {
    min: 2,
    max: 5,
    label: 'Initiative',
    hint: 'How much I bring up on my own.',
  },
} as const

export type DialKey = keyof typeof DIAL_RANGES

export function dialValue(
  effective: Record<string, unknown>,
  key: DialKey,
  fallback: number,
): number {
  const value = effective[key]
  if (typeof value === 'number' && Number.isFinite(value)) return value
  return fallback
}

/**
 * A sample line, tuned on the client as the dials move.
 *
 * It is a preview, not a promise: the real Wren reads the saved dials.
 */
export function tuneLine(sample: string, dials: Dials): string {
  if (dials.humor >= 5 && dials.warmth >= 6) {
    return `${sample} Nice weather for it.`
  }
  if (dials.directness >= 7 && dials.warmth <= 6) {
    const firstSentence = sample.split('.')[0]
    return `${firstSentence}.`
  }
  if (dials.warmth >= 8) {
    return `${sample} Take your time.`
  }
  return sample
}

export function StepDials({
  initialDials,
  sampleLine,
  pending,
  error,
  onSubmit,
}: {
  initialDials: Dials
  sampleLine: string
  pending: boolean
  error: string | null
  onSubmit: (dials: Dials) => void
}) {
  const [dials, setDials] = useState<Dials>(initialDials)

  return (
    <div className="flex max-w-2xl flex-col gap-10">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl">Tune this Wren.</h1>
        <p className="mt-4 leading-relaxed text-[var(--wren-ink-muted)]">
          These are the dials I answer on. Move them and the sample line below
          changes with you. Nothing here is a promise about how I will feel
          about your messages — it is how I am built.
        </p>
      </div>

      <div className="flex flex-col gap-8">
        {(Object.keys(DIAL_RANGES) as DialKey[]).map((key) => {
          const range = DIAL_RANGES[key]
          return (
            <div key={key} className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between">
                <label
                  htmlFor={`dial-${key}`}
                  className="font-medium capitalize"
                >
                  {range.label}
                </label>
                <span className="text-sm text-[var(--wren-ink-muted)]">
                  {dials[key]}
                </span>
              </div>
              <Slider
                id={`dial-${key}`}
                aria-label={range.label}
                min={range.min}
                max={range.max}
                step={1}
                value={[dials[key]]}
                onValueChange={([value]) => {
                  if (typeof value === 'number') {
                    setDials((current) => ({ ...current, [key]: value }))
                  }
                }}
              />
              <p className="text-xs text-[var(--wren-ink-muted)]">
                {range.hint}
              </p>
            </div>
          )
        })}
      </div>

      <div className="wren-card p-6">
        <p className="text-xs uppercase tracking-[0.15em] text-[var(--wren-ink-muted)]">
          Sample line
        </p>
        <p className="mt-3 leading-relaxed">“{tuneLine(sampleLine, dials)}”</p>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-[#a2442c]">
          {error}
        </p>
      ) : null}

      <div>
        <Button
          onClick={() => onSubmit(dials)}
          disabled={pending}
          className="rounded-full px-6 py-2.5"
        >
          {pending ? 'Saving…' : 'Continue'}
        </Button>
      </div>
    </div>
  )
}
