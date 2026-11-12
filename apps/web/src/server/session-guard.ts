import { me } from './auth'
import { guardRedirect, type GuardRedirect } from '~/lib/guards'

/**
 * The guard every protected route runs in `beforeLoad`.
 *
 * The session is read on the server, so the decision is made before any
 * protected content is sent to the browser.
 */
export async function sessionGuard(
  path: string,
): Promise<GuardRedirect | undefined> {
  const result = await me()
  const user = result.ok ? result.data : null
  return guardRedirect(path, user)
}
