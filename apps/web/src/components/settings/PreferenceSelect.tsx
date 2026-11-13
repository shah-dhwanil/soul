import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select'

export interface PreferenceOption {
  value: string
  label: string
}

/**
 * One preference. The options are exactly the ones the API accepts.
 */
export function PreferenceSelect({
  id,
  label,
  hint,
  value,
  options,
  onChange,
}: {
  id: string
  label: string
  hint: string
  value: string
  options: PreferenceOption[]
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="font-medium">
        {label}
      </label>
      <Select value={value} onValueChange={(next) => onChange(next)}>
        <SelectTrigger id={id} aria-label={label} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-xs text-[var(--wren-ink-muted)]">{hint}</p>
    </div>
  )
}
