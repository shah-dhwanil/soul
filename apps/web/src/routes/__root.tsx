/// <reference types="vite/client" />
import {
  HeadContent,
  Link,
  Outlet,
  Scripts,
  createRootRouteWithContext,
} from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import * as React from 'react'
import type { QueryClient } from '@tanstack/react-query'
import appCss from '~/styles/app.css?url'
import { me } from '~/server/auth'

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  loader: async () => {
    const result = await me()
    return { user: result.ok ? result.data : null }
  },
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'Wren' },
      {
        name: 'description',
        content:
          'A steady friend who pays attention, tells you the truth once, and becomes recognizably yours the longer you talk.',
      },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      {
        rel: 'preconnect',
        href: 'https://fonts.gstatic.com',
        crossOrigin: 'anonymous',
      },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap',
      },
    ],
  }),
  component: RootComponent,
})

function RootComponent() {
  const { queryClient } = Route.useRouteContext()
  const { user } = Route.useLoaderData()
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body className="bg-[var(--wren-bg)] text-[var(--wren-ink)] antialiased">
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-dvh flex-col">
            <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6">
              <Link to="/" className="font-display text-lg tracking-tight">
                Wren
              </Link>
              <nav className="flex items-center gap-4 text-sm">
                {user ? (
                  <Link
                    to="/chat"
                    className="rounded-full bg-[var(--wren-accent)] px-4 py-2 text-[var(--wren-ink)] transition-opacity hover:opacity-90"
                  >
                    Chat
                  </Link>
                ) : (
                  <Link
                    to="/onboarding"
                    className="rounded-full bg-[var(--wren-accent)] px-4 py-2 text-[var(--wren-ink)] transition-opacity hover:opacity-90"
                  >
                    Begin
                  </Link>
                )}
              </nav>
            </header>
            <main className="flex-1">
              <Outlet />
            </main>
          </div>
        </QueryClientProvider>
        <Scripts />
      </body>
    </html>
  )
}
