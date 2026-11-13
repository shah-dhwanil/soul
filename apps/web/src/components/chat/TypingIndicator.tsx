/**
 * Wren is typing.
 */
export function TypingIndicator() {
  return (
    <div
      data-testid="typing"
      role="status"
      aria-label="Wren is thinking"
      className="flex items-center gap-1.5 px-5 py-3"
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="size-2 animate-pulse rounded-full bg-[var(--wren-ink-muted)]"
          style={{ animationDelay: `${index * 160}ms` }}
        />
      ))}
    </div>
  )
}
