export function FactList({ facts }: { facts: string[] }) {
  if (facts.length === 0) {
    return (
      <p className="text-sm text-[var(--wren-ink-muted)]">
        Wren hasn’t learned this about you yet.
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-2">
      {facts.map((fact, index) => (
        <li
          key={`${fact}-${index}`}
          data-reveal
          className="flex items-start gap-3 px-1 py-1 leading-relaxed"
        >
          <span
            aria-hidden
            className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--wren-accent)]"
          />
          <span>{fact}</span>
        </li>
      ))}
    </ul>
  )
}
