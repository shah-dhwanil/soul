import { useEffect, useRef } from 'react'
import { Button } from '~/components/ui/button'
import gsap from 'gsap'

/**
 * The payoff: the line Wren opens with, chosen by the temperament the user
 * picked in the duel.
 */
export function OpeningReveal({
  firstLine,
  pending,
  error,
  onContinue,
}: {
  firstLine: string
  pending: boolean
  error: string | null
  onContinue: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const targets = element.querySelectorAll('[data-reveal]')
    // A context reverts the styles it changed, so an interrupted reveal
    // never leaves the opening line half hidden.
    const context = gsap.context(() => {
      gsap.fromTo(
        targets,
        { autoAlpha: 0, y: 20 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.8,
          ease: 'power2.out',
          stagger: 0.15,
          delay: 0.1,
          onComplete: () => {
            gsap.set(targets, { clearProps: 'all' })
          },
        },
      )
    }, element)
    return () => {
      context.revert()
    }
  }, [ref])

  return (
    <div ref={ref} className="flex max-w-2xl flex-col gap-8">
      <div>
        <h1 data-reveal className="font-display text-3xl sm:text-4xl">
          Here we go.
        </h1>
        <p
          data-reveal
          className="mt-6 font-display text-xl leading-relaxed sm:text-2xl"
        >
          “{firstLine}”
        </p>
        <p data-reveal className="mt-4 text-[var(--wren-ink-muted)]">
          That is my opening line. It is what I will say first when you come
          back.
        </p>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-[#a2442c]">
          {error}
        </p>
      ) : null}

      <div data-reveal>
        <Button
          onClick={onContinue}
          disabled={pending}
          className="rounded-full px-6 py-2.5"
        >
          {pending ? 'One moment…' : 'Start talking'}
        </Button>
      </div>
    </div>
  )
}
