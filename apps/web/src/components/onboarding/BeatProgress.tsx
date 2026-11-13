import type { BeatKey } from '~/lib/onboarding'

export type { BeatKey }

/** The beats of the arc, in order. Never shown as "step 2 of 4". */
export const BEATS: Array<{ key: BeatKey; label: string }> = [
  { key: 'account', label: 'Account' },
  { key: 'meet', label: 'First meeting' },
  { key: 'duel', label: 'Temperament' },
  { key: 'name', label: 'Your name' },
  { key: 'dials', label: 'The dials' },
  { key: 'reveal', label: 'First words' },
]

export function BeatProgress({
  current,
  completed,
}: {
  current: BeatKey
  completed: BeatKey[]
}) {
  const currentIndex = BEATS.findIndex((beat) => beat.key === current)
  const label = BEATS[currentIndex]?.label ?? ''

  return (
    <div className="flex items-center gap-3" aria-label={`Progress: ${label}`}>
      <ol className="flex items-center gap-2">
        {BEATS.map((beat, index) => {
          const isDone = completed.includes(beat.key)
          const isCurrent = beat.key === current
          return (
            <li
              key={beat.key}
              aria-current={isCurrent ? 'step' : undefined}
              className={`h-2 w-2 rounded-full transition-colors ${
                isDone
                  ? 'bg-[var(--wren-accent)]'
                  : isCurrent
                    ? 'bg-[var(--wren-ink)]'
                    : 'bg-[var(--wren-border)]'
              }`}
            />
          )
        })}
      </ol>
      <span className="text-sm text-[var(--wren-ink-muted)]">{label}</span>
    </div>
  )
}
