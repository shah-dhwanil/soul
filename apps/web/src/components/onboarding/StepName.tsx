import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'

/**
 * The name beat. Required: Wren needs to know what to call you.
 */
export function StepName({
  initialName,
  pending,
  error,
  onSubmit,
}: {
  initialName: string
  pending: boolean
  error: string | null
  onSubmit: (address: string) => void
}) {
  const [address, setAddress] = useState(initialName)
  const trimmed = address.trim()
  const canSubmit = trimmed.length > 0 && trimmed.length <= 80

  return (
    <div className="flex max-w-xl flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl sm:text-4xl">
          What should I call you?
        </h1>
        <p className="mt-4 leading-relaxed text-[var(--wren-ink-muted)]">
          A name, a nickname, whatever you would like to hear. I will use it
          from now on.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="address">Your name</Label>
        <Input
          id="address"
          name="address"
          maxLength={80}
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && canSubmit) {
              event.preventDefault()
              onSubmit(trimmed)
            }
          }}
        />
        <p className="text-xs text-[var(--wren-ink-muted)]">
          {address.trim().length}/80
        </p>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-[#a2442c]">
          {error}
        </p>
      ) : null}

      <div>
        <Button
          onClick={() => onSubmit(trimmed)}
          disabled={!canSubmit || pending}
          className="rounded-full px-6 py-2.5"
        >
          {pending ? 'Saving…' : 'Continue'}
        </Button>
      </div>
    </div>
  )
}
