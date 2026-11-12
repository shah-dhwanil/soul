import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { Button } from '~/components/ui/button'
import type { Temperament } from '~/lib/types'

/** Round one is fixed: these are the pairings Wren is described with. */
const FIRST_ROUND: Array<[string, string]> = [
  ['steady', 'wry'],
  ['gentle', 'tinker'],
]

function findSeed(
  temperaments: Temperament[],
  id: string,
): Temperament | undefined {
  return temperaments.find((temperament) => temperament.id === id)
}

/**
 * The temperament tournament: four seeds, two matches, one winner.
 *
 * Nothing is saved until the final pick — the bracket is a local decision.
 */
export function TemperamentDuel({
  temperaments,
  pending,
  error,
  onComplete,
}: {
  temperaments: Temperament[]
  pending: boolean
  error: string | null
  onComplete: (winnerId: string) => void
}) {
  const [round, setRound] = useState(0)
  const [winners, setWinners] = useState<string[]>([])
  const [picks, setPicks] = useState<Record<string, string>>({})
  const [eliminated, setEliminated] = useState<string[]>([])
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const roundRef = useRef<HTMLDivElement>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const matches: Array<[string, string]> =
    round === 0 ? FIRST_ROUND : [winners as [string, string]]

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  useEffect(() => {
    const element = roundRef.current
    if (!element) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const tween = gsap.fromTo(
      element.children,
      { autoAlpha: 0, y: 18 },
      { autoAlpha: 1, y: 0, duration: 0.5, ease: 'power2.out', stagger: 0.12 },
    )
    return () => {
      tween.kill()
    }
  }, [round, winners])

  function choose(matchIndex: number, chosenId: string, otherId: string) {
    const key = `${round}:${matchIndex}`
    if (picks[key]) return

    const nextPicks = { ...picks, [key]: chosenId }
    setPicks(nextPicks)

    const loser = cardRefs.current[otherId]
    const hide = () =>
      setEliminated((current) =>
        current.includes(otherId) ? current : [...current, otherId],
      )
    if (loser && !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      gsap.to(loser, { autoAlpha: 0, scale: 0.96, duration: 0.35, onComplete: hide })
    } else {
      hide()
    }

    // Every match in this round is decided: move on.
    if (matches.every((_, index) => nextPicks[`${round}:${index}`])) {
      timer.current = setTimeout(() => {
        if (round === 0) {
          const decided = matches.map(
            (_, index) => nextPicks[`${round}:${index}`] as string,
          )
          setWinners(decided)
          setPicks({})
          setEliminated([])
          setRound(1)
        } else {
          const champion = nextPicks[`${round}:0`]
          if (champion) onComplete(champion)
        }
      }, 700)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="max-w-xl">
        <h1 className="font-display text-3xl sm:text-4xl">
          {round === 0 ? 'Four ways of being.' : 'And the last one standing.'}
        </h1>
        <p className="mt-4 text-[var(--wren-ink-muted)]">
          {round === 0
            ? 'Two matches first. Keep the one you would rather talk to.'
            : 'One more. This is the one that becomes me.'}
        </p>
      </div>

      <div ref={roundRef} className="flex flex-col gap-10">
        {matches.map(([a, b], matchIndex) => {
          const key = `${round}:${matchIndex}`
          const chosen = picks[key]
          return (
            <div
              key={key}
              className="grid gap-6 sm:grid-cols-2"
              data-testid={`match-${matchIndex}`}
            >
              {[a, b].map((id) => {
                const seed = findSeed(temperaments, id)
                if (!seed) return null
                const isChosen = chosen === id
                const isOut = eliminated.includes(id)
                if (isOut) return null
                return (
                  <div
                    key={id}
                    ref={(element) => {
                      cardRefs.current[id] = element
                    }}
                    className={`wren-card flex flex-col gap-4 p-6 transition-shadow ${
                      isChosen
                        ? 'ring-2 ring-[var(--wren-accent)]'
                        : 'hover:shadow-md'
                    }`}
                    data-testid={`seed-${id}`}
                  >
                    <h2 className="font-display text-2xl capitalize">{seed.id}</h2>
                    <p className="text-sm text-[var(--wren-ink-muted)]">
                      {seed.feelsLike}
                    </p>
                    <p className="leading-relaxed">“{seed.sampleReply}”</p>
                    <Button
                      variant={isChosen ? 'default' : 'outline'}
                      disabled={Boolean(chosen) || pending}
                      onClick={() =>
                        choose(
                          matchIndex,
                          id,
                          id === a ? b : a,
                        )
                      }
                      className="rounded-full self-start"
                    >
                      {isChosen ? 'Kept' : 'Keep this one'}
                    </Button>
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>

      {error ? (
        <p role="alert" className="text-sm text-[#a2442c]">
          {error}
        </p>
      ) : null}
    </div>
  )
}
