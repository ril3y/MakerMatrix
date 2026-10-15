import { test, expect } from '@playwright/test'

// Visual regression for the unauthenticated entry point. The login page needs
// no backend data, so it renders identically on every run. Baselines live in
// login.visual.spec.ts-snapshots/ and are generated on the CI Linux runner
// (`npm run test:visual -- --update-snapshots`) so fonts/rendering match.
test.describe('Visual regression', () => {
  test('login page', async ({ page }) => {
    // AuthLayout runs infinite framer-motion animations (gradient orbs,
    // floating icons, spinning logo) driven by requestAnimationFrame. Take
    // over the clock and pause it at a fixed instant (well past the entry
    // fade-ins) so every run captures the same animation frame regardless of
    // how long the page took to load.
    await page.clock.install({ time: new Date('2026-01-01T00:00:00Z') })
    await page.goto('/login')
    await expect(page.getByText('Welcome Back')).toBeVisible()
    await page.clock.pauseAt(new Date('2026-01-01T00:01:00Z'))

    await expect(page).toHaveScreenshot('login.png', {
      fullPage: true,
      animations: 'disabled',
      maxDiffPixelRatio: 0.01,
    })
  })
})
