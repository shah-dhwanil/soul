import type { Trait } from '~/lib/types'

/** A date the way a person would say it. */
export function formatDate(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export function TraitList({ traits }: { traits: Trait[] }) {
  if (traits.length === 0) {
    return (
      <p className="text-sm text-[var(--wren-ink-muted)]">
        Wren hasn’t learned this about you yet.
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-3">
      {traits.map((trait) => {
        const landed = formatDate(trait.lastLanded)
        return (
          <li
            key={trait.id}
            data-reveal
            className="wren-card flex flex-wrap items-baseline justify-between gap-2 px-5 py-4"
          >
            <span className="font-medium">{trait.label}</span>
            <span className="text-xs text-[var(--wren-ink-muted)]">
              {trait.kind}
              {landed ? ` · last used ${landed}` : ''}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
