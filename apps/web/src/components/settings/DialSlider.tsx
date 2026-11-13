import { Slider } from '~/components/ui/slider'

/**
 * One dial. The ranges are the API's: the UI cannot offer anything else.
 */
export function DialSlider({
  id,
  label,
  hint,
  min,
  max,
  value,
  isDefault,
  onChange,
}: {
  id: string
  label: string
  hint: string
  min: number
  max: number
  value: number
  isDefault: boolean
  onChange: (value: number) => void
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="font-medium">
          {label}
        </label>
        <span className="flex items-center gap-2 text-sm text-[var(--wren-ink-muted)]">
          {isDefault ? (
            <span className="rounded-full bg-[var(--wren-accent-soft)] px-2 py-0.5 text-xs">
              temperament default
            </span>
          ) : null}
          {value}
        </span>
      </div>
      <Slider
        id={id}
        aria-label={label}
        min={min}
        max={max}
        step={1}
        value={[value]}
        onValueChange={([next]) => {
          if (typeof next === 'number') onChange(next)
        }}
      />
      <p className="text-xs text-[var(--wren-ink-muted)]">{hint}</p>
    </div>
  )
}
