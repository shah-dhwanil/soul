import { useEffect, type RefObject } from 'react'
import gsap from 'gsap'

/**
 * Motion.
 *
 * Everything here is decorative: with `prefers-reduced-motion` set, nothing
 * animates and every element is simply visible.
 */

export interface RevealOptions {
  /** Distance in pixels the elements rise from. */
  y?: number
  /** Seconds between each revealed child. */
  stagger?: number
  /** Delay before the first reveal. */
  delay?: number
  /** ScrollTrigger start position. */
  start?: string
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return true
  if (!window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Reveal the `[data-reveal]` children of `ref` once they scroll into view.
 *
 * The ScrollTrigger plugin is imported lazily: it only exists in the browser,
 * and the landing page is rendered on the server too.
 */
export function useReveal(
  ref: RefObject<HTMLElement | null>,
  options: RevealOptions = {},
): void {
  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (prefersReducedMotion()) return

    let cancelled = false
    let context: gsap.Context | undefined

    void import('gsap/ScrollTrigger').then(({ ScrollTrigger }) => {
      if (cancelled) return
      gsap.registerPlugin(ScrollTrigger)
      const targets = element.querySelectorAll('[data-reveal]')
      if (targets.length === 0) return
      context = gsap.context(() => {
        gsap.fromTo(
          targets,
          { autoAlpha: 0, y: options.y ?? 24 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.7,
            ease: 'power2.out',
            stagger: options.stagger ?? 0.08,
            delay: options.delay ?? 0,
            scrollTrigger: {
              trigger: element,
              start: options.start ?? 'top 80%',
              once: true,
            },
          },
        )
      }, element)
    })

    return () => {
      cancelled = true
      context?.revert()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref])
}

/** The hero's entrance on load. */
export function useEntrance(
  ref: RefObject<HTMLElement | null>,
  options: RevealOptions = {},
): void {
  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (prefersReducedMotion()) return
    const targets = element.querySelectorAll('[data-reveal]')
    if (targets.length === 0) return
    const tween = gsap.fromTo(
      targets,
      { autoAlpha: 0, y: options.y ?? 18 },
      {
        autoAlpha: 1,
        y: 0,
        duration: 0.8,
        ease: 'power2.out',
        stagger: options.stagger ?? 0.1,
        delay: options.delay ?? 0.1,
      },
    )
    return () => {
      tween.kill()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref])
}
