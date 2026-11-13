import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { Notice } from './Notice'
import { unanimatedWrenBubbles, type TranscriptItem } from '~/lib/chat'
import { prefersReducedMotion } from '~/lib/motion'

function Bubble({ role, text }: { role: 'wren' | 'user'; text: string }) {
  const isWren = role === 'wren'
  return (
    <div
      data-testid="bubble"
      data-role={role}
      className={`flex ${isWren ? 'justify-start' : 'justify-end'}`}
    >
      <div
        className={`max-w-[85%] rounded-3xl px-5 py-3 leading-relaxed whitespace-pre-wrap ${
          isWren
            ? 'wren-card rounded-bl-md'
            : 'bg-[var(--wren-accent-soft)] rounded-br-md'
        }`}
      >
        {text}
      </div>
    </div>
  )
}

function Divider({ label }: { label: string }) {
  return (
    <div
      data-testid="divider"
      className="flex items-center gap-4 py-2 text-xs uppercase tracking-[0.2em] text-[var(--wren-ink-muted)]"
    >
      <span className="h-px flex-1 bg-[var(--wren-border)]" />
      <span>{label}</span>
      <span className="h-px flex-1 bg-[var(--wren-border)]" />
    </div>
  )
}

/**
 * The transcript. Wren's bubbles reveal with a soft fade; user text is
 * rendered as text, never as markup.
 */
export function MessageList({ items }: { items: TranscriptItem[] }) {
  const [dismissed, setDismissed] = useState<string[]>([])
  const ref = useRef<HTMLDivElement>(null)
  const tweens = useRef<gsap.core.Tween[]>([])
  const revealed = useRef<Element[]>([])

  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (prefersReducedMotion()) return
    // Only the new bubbles animate: the history must not blink on every reply.
    const bubbles = unanimatedWrenBubbles(element)
    if (bubbles.length === 0) return
    revealed.current.push(...bubbles)
    const tween = gsap.fromTo(
      bubbles,
      { autoAlpha: 0, y: 10 },
      {
        autoAlpha: 1,
        y: 0,
        duration: 0.5,
        ease: 'power2.out',
        stagger: 0.08,
        // Hand the styles back when the reveal is done, so the bubble is
        // exactly as visible as the others.
        onComplete: () => {
          gsap.set(bubbles, { clearProps: 'all' })
        },
      },
    )
    tweens.current.push(tween)
  }, [items])

  useEffect(() => {
    return () => {
      for (const tween of tweens.current) tween.kill()
      // A reveal that is interrupted must not leave a bubble half hidden.
      gsap.set(revealed.current, { clearProps: 'all' })
      for (const bubble of revealed.current) {
        bubble.removeAttribute('data-animated')
      }
    }
  }, [])

  return (
    <div ref={ref} className="flex flex-col gap-4" data-testid="transcript">
      {items.map((item) => {
        if (item.type === 'divider') {
          return <Divider key={item.id} label={item.label} />
        }
        if (item.type === 'notice') {
          if (dismissed.includes(item.id)) return null
          return (
            <Notice
              key={item.id}
              text={item.text}
              onDismiss={() =>
                setDismissed((current) => [...current, item.id])
              }
            />
          )
        }
        return <Bubble key={item.id} role={item.role} text={item.text} />
      })}
    </div>
  )
}
