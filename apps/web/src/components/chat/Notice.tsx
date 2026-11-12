import { X } from 'lucide-react'

/**
 * A small, dismissible inline notice. Never an error state.
 */
export function Notice({
  text,
  onDismiss,
}: {
  text: string
  onDismiss: () => void
}) {
  return (
    <div
      role="status"
      data-testid="notice"
      className="flex items-start gap-3 rounded-2xl border border-[var(--wren-border)] bg-[var(--wren-accent-soft)] px-4 py-3 text-sm"
    >
      <p className="flex-1 leading-relaxed">{text}</p>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className="rounded-full p-1 transition-opacity hover:opacity-70"
      >
        <X className="size-4" />
      </button>
    </div>
  )
}
