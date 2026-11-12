import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { login, me } from '~/server/auth'

/** Where the user lands after signing in. */
function landingPath(next: string | undefined, onboarded: boolean): string {
  if (next && ['/chat', '/settings', '/you', '/onboarding'].includes(next)) {
    return next
  }
  return onboarded ? '/chat' : '/onboarding'
}

/**
 * One message for a wrong email and a wrong password: the form never says
 * which one it was.
 */
function errorMessage(code: string): string {
  switch (code) {
    case 'invalid_credentials':
      return 'That email and password do not match.'
    case 'rate_limited':
      return 'Too many attempts. Give it a minute and try again.'
    default:
      return 'Something went wrong. Try again in a moment.'
  }
}

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>) => {
    const next = typeof search.next === 'string' ? search.next : undefined
    return next ? { next } : {}
  },
  beforeLoad: async ({ location, search }) => {
    const result = await me()
    const user = result.ok ? result.data : null
    if (user) {
      throw redirect({
        href: landingPath(search.next, user.onboarded),
      })
    }
  },
  component: LoginPage,
})

function LoginPage() {
  const { next } = Route.useSearch()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError(null)
    const result = await login({ data: { email, password } })
    setPending(false)
    if (!result.ok) {
      setError(errorMessage(result.code))
      return
    }
    await navigate({ href: landingPath(next, result.data.onboarded) })
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col px-6 py-24">
      <div className="wren-card p-8">
        <h1 className="font-display text-3xl">Welcome back.</h1>
        <p className="mt-2 text-sm text-[var(--wren-ink-muted)]">
          Sign in to pick up where you left off.
        </p>

        <form className="mt-8 flex flex-col gap-5" onSubmit={onSubmit}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error ? (
            <p role="alert" className="text-sm text-[#a2442c]">
              {error}
            </p>
          ) : null}

          <Button
            type="submit"
            disabled={pending}
            className="rounded-full py-2.5"
          >
            {pending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-[var(--wren-ink-muted)]">
        New here?{' '}
        <a href="/onboarding" className="underline underline-offset-4">
          Start a conversation
        </a>
      </p>
    </div>
  )
}
