import { Link } from '@tanstack/react-router'
import { navLinks } from '~/lib/nav'
import type { AuthUser } from '~/lib/types'

/**
 * The header: the way into the product, and the way out of it.
 */
export function AppNav({
  user,
  onSignOut,
}: {
  user: AuthUser | null
  onSignOut: () => void
}) {
  const links = navLinks(user)

  return (
    <nav className="flex items-center gap-4 text-sm">
      {links.map((link) => (
        <Link
          key={link.to}
          to={link.to}
          className={
            link.to === '/chat'
              ? 'rounded-full bg-[var(--wren-accent)] px-4 py-2 text-[var(--wren-ink)] transition-opacity hover:opacity-90'
              : 'rounded-full px-3 py-2 text-[var(--wren-ink-muted)] underline-offset-4 transition-colors hover:text-[var(--wren-ink)] hover:underline'
          }
        >
          {link.label}
        </Link>
      ))}

      {user ? (
        <button
          type="button"
          onClick={onSignOut}
          className="rounded-full px-3 py-2 text-[var(--wren-ink-muted)] underline-offset-4 transition-colors hover:text-[var(--wren-ink)] hover:underline"
        >
          Sign out
        </button>
      ) : null}
    </nav>
  )
}
