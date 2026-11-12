import { describe, expect, test, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router'
import { AppNav } from '~/components/shared/AppNav'
import { navLinks } from '~/lib/nav'
import type { AuthUser } from '~/lib/types'

const signedIn: AuthUser = {
  userId: 'u1',
  email: 'a@b.co',
  onboarded: true,
  onboardingStep: 4,
}

async function renderNav(user: AuthUser | null, onSignOut?: () => void) {
  const rootRoute = createRootRoute({
    component: () => (
      <AppNav user={user} onSignOut={onSignOut ?? (() => {})} />
    ),
  })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  await router.load()
  return render(<RouterProvider router={router} />)
}

describe('navigation', () => {
  test('a signed out visitor is offered one way in', () => {
    expect(navLinks(null)).toEqual([{ to: '/onboarding', label: 'Begin' }])
  })

  test('a signed in visitor can reach chat, you, and settings', () => {
    expect(navLinks(signedIn)).toEqual([
      { to: '/chat', label: 'Chat' },
      { to: '/you', label: 'You' },
      { to: '/settings', label: 'Settings' },
    ])
  })

  test('the nav renders those links', async () => {
    await renderNav(signedIn)
    expect(screen.getByRole('link', { name: 'Chat' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'You' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Settings' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /sign out/i })).toBeTruthy()
  })

  test('signing out is offered to a signed in visitor', async () => {
    const onSignOut = vi.fn()
    await renderNav(signedIn, onSignOut)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(onSignOut).toHaveBeenCalled()
  })

  test('a signed out visitor sees no sign out', async () => {
    await renderNav(null)
    expect(screen.queryByRole('button', { name: /sign out/i })).toBeNull()
  })
})
