import type { AuthUser } from '~/lib/types'

/**
 * Where the header takes someone.
 *
 * A signed out visitor has one way in; a signed in one can reach the
 * conversation, what Wren has noticed, and the settings.
 */
export function navLinks(
  user: AuthUser | null,
): Array<{ to: string; label: string }> {
  if (!user) {
    return [{ to: '/onboarding', label: 'Begin' }]
  }
  return [
    { to: '/chat', label: 'Chat' },
    { to: '/you', label: 'You' },
    { to: '/settings', label: 'Settings' },
  ]
}
