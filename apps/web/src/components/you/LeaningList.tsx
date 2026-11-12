import type { Leaning } from '~/lib/types'

export function LeaningList({ leanings }: { leanings: Leaning[] }) {
  if (leanings.length === 0) {
    return (
      <p className="text-sm text-[var(--wren-ink-muted)]">
        Wren hasn’t learned this about you yet.
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-3">
      {leanings.map((leaning) => (
        <li
          key={leaning.id}
          data-reveal
          className="wren-card flex flex-wrap items-baseline justify-between gap-2 px-5 py-4"
        >
          <span>{leaning.value}</span>
          <span className="text-xs text-[var(--wren-ink-muted)]">
            {leaning.kind}
          </span>
        </li>
      ))}
    </ul>
  )
}
