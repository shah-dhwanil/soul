import { useEffect, useRef } from 'react'
import { Button } from '~/components/ui/button'
import gsap from 'gsap'

/**
 * The beat that frames the duel: one short paragraph, no inputs.
 */
export function MeetFrame({ onContinue }: { onContinue: () => void }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const tween = gsap.fromTo(
      element.querySelectorAll('[data-reveal]'),
      { autoAlpha: 0, y: 16 },
      { autoAlpha: 1, y: 0, duration: 0.6, ease: 'power2.out', stagger: 0.12 },
    )
    return () => {
      tween.kill()
    }
  }, [ref])

  return (
    <div ref={ref} className="flex flex-col gap-8">
      <div className="max-w-xl">
        <h1 data-reveal className="font-display text-3xl sm:text-4xl">
          One question first.
        </h1>
        <p
          data-reveal
          className="mt-5 text-lg leading-relaxed text-[var(--wren-ink-muted)]"
        >
          I come in four ways, and only one of them ends up being me. Two will
          talk it out, then the winner goes on to meet the other winner. Pick
          the one you would rather talk to at midnight. You can change it
          later.
        </p>
      </div>
      <div data-reveal>
        <Button onClick={onContinue} className="rounded-full px-6 py-2.5">
          Show me
        </Button>
      </div>
    </div>
  )
}
