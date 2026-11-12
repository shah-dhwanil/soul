import { createFileRoute, redirect } from '@tanstack/react-router'
import { useRef } from 'react'
import { FactList } from '~/components/you/FactList'
import { LeaningList } from '~/components/you/LeaningList'
import { TraitList } from '~/components/you/TraitList'
import { useReveal } from '~/lib/motion'
import { sessionGuard } from '~/server/session-guard'
import { fetchYou } from '~/server/wren'

export const Route = createFileRoute('/you')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  loader: async () => {
    const result = await fetchYou()
    return {
      view: result.ok
        ? result.data
        : { traits: [], leanings: [], facts: [] },
    }
  },
  component: YouPage,
})

function YouPage() {
  const { view } = Route.useLoaderData()
  const ref = useRef<HTMLDivElement>(null)
  useReveal(ref, { stagger: 0.06 })

  return (
    <div ref={ref} className="mx-auto w-full max-w-3xl px-6 py-12">
      <h1 className="font-display text-3xl">How Wren sees you today.</h1>
      <p className="mt-3 max-w-prose text-[var(--wren-ink-muted)]">
        Everything Wren has picked up from talking with you. It is only ever
        shown — nothing here can be changed or deleted.
      </p>

      <section className="mt-12 flex flex-col gap-4">
        <h2 className="font-display text-xl">Traits</h2>
        <TraitList traits={view.traits} />
      </section>

      <section className="mt-12 flex flex-col gap-4">
        <h2 className="font-display text-xl">Leanings</h2>
        <LeaningList leanings={view.leanings} />
      </section>

      <section className="mt-12 flex flex-col gap-4">
        <h2 className="font-display text-xl">What you have told Wren</h2>
        <FactList facts={view.facts} />
      </section>
    </div>
  )
}
