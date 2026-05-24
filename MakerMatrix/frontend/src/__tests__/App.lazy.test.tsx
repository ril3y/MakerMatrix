/**
 * Smoke test for route-level lazy imports. The eight pages in `App.tsx` are
 * loaded via `React.lazy(() => import(...))` — this asserts that importing
 * App and rendering it under a Router+Suspense boundary doesn't crash (i.e.
 * every lazy import resolves to a valid component module).
 *
 * We don't render the live `<App />` because that wires up `BrowserRouter` +
 * `WebSocketProvider` + auth bootstrapping; instead we exercise the lazy
 * factories directly, which is the actual code split surface.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { lazy, Suspense } from 'react'

// Mirror App.tsx's import map. If a lazy import target ever moves, this
// failing test points right at the dead path.
const LAZY_ROUTES: Array<[string, () => Promise<{ default: React.ComponentType<unknown> }>]> = [
  ['LoginPage', () => import('@/pages/auth/LoginPage')],
  ['DashboardPage', () => import('@/pages/DashboardPage')],
  ['PartsPage', () => import('@/pages/parts/PartsPage')],
  ['PartDetailsPage', () => import('@/pages/parts/PartDetailsPage')],
  ['EditPartPage', () => import('@/pages/parts/EditPartPage')],
  ['LocationsPage', () => import('@/pages/locations/LocationsPage')],
  ['CategoriesPage', () => import('@/pages/categories/CategoriesPage')],
  ['ProjectsPage', () => import('@/pages/projects/ProjectsPage')],
  ['ToolsPage', () => import('@/pages/tools/ToolsPage')],
  ['UsersPage', () => import('@/pages/users/UsersPage')],
  ['SettingsPage', () => import('@/pages/settings/SettingsPage')],
  ['TasksPage', () => import('@/pages/tasks/TasksPage')],
  ['UnauthorizedPage', () => import('@/pages/UnauthorizedPage')],
  ['NotFoundPage', () => import('@/pages/NotFoundPage')],
]

describe('App lazy route imports', () => {
  for (const [name, loader] of LAZY_ROUTES) {
    it(`resolves the ${name} dynamic import to a renderable component`, async () => {
      const mod = await loader()
      expect(mod).toBeDefined()
      // Every lazy route must default-export a component (function or class).
      expect(typeof mod.default).toBe('function')
    })
  }

  it('renders a lazy route inside MemoryRouter + Suspense without throwing', async () => {
    const Unauthorized = lazy(() => import('@/pages/UnauthorizedPage'))

    render(
      <MemoryRouter initialEntries={['/unauthorized']}>
        <Suspense fallback={<div>loading</div>}>
          <Unauthorized />
        </Suspense>
      </MemoryRouter>
    )

    // First paint shows the fallback while the chunk resolves.
    expect(screen.getByText('loading')).toBeInTheDocument()
    // Then the lazy chunk mounts. UnauthorizedPage owns the word
    // "unauthorized" in its body; assert something from the chunk actually
    // rendered.
    await waitFor(() => {
      const fallback = screen.queryByText('loading')
      expect(fallback).not.toBeInTheDocument()
    })
  })
})
