import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import type { AuthUser } from '~/lib/types'

/**
 * The account beat: a plain sign-up screen, no story chrome.
 *
 * `variant="register"` is the same form used by the login page when a
 * visitor has no account yet.
 */
export function StepAccount({
  user,
  pending,
  error,
  variant = 'beat',
  onRegister,
  onContinue,
}: {
  user: AuthUser | null
  pending: boolean
  error: string | null
  variant?: 'beat' | 'register'
  onRegister: (email: string, password: string) => void
  onContinue: () => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  if (user && variant === 'beat') {
    return (
      <div className="wren-card flex flex-col gap-6 p-8">
        <div>
          <h1 className="font-display text-2xl">You’re signed in.</h1>
          <p className="mt-2 text-sm text-[var(--wren-ink-muted)]">
            Signed in as {user.email}. We can pick up from here.
          </p>
        </div>
        <Button onClick={onContinue} className="rounded-full py-2.5">
          Continue
        </Button>
      </div>
    )
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    if (password.length < 8) {
      setLocalError('Use at least 8 characters for the password.')
      return
    }
    setLocalError(null)
    onRegister(email, password)
  }

  return (
    <div className="wren-card flex flex-col gap-6 p-8">
      <div>
        <h1 className="font-display text-2xl">Make an account.</h1>
        <p className="mt-2 text-sm text-[var(--wren-ink-muted)]">
          An email and a password. That is the whole thing.
        </p>
      </div>

      <form className="flex flex-col gap-5" method="post" onSubmit={submit}>
        <div className="flex flex-col gap-2">
          <Label htmlFor="onboarding-email">Email</Label>
          <Input
            id="onboarding-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="onboarding-password">Password</Label>
          <Input
            id="onboarding-password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        {localError || error ? (
          <p role="alert" className="text-sm text-[#a2442c]">
            {localError ?? error}
          </p>
        ) : null}

        <Button
          type="submit"
          disabled={pending}
          className="rounded-full py-2.5"
        >
          {pending ? 'Making your account…' : 'Create account'}
        </Button>
      </form>
    </div>
  )
}
