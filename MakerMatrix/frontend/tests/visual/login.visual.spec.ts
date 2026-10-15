import { test, expect } from '@playwright/test'

// Visual regression for the unauthenticated entry point. The login page needs
// no backend data, so it renders identically on every run. Baselines live in
// login.visual.spec.ts-snapshots/ and are generated on the CI Linux runner
// (`npm run test:visual -- --update-snapshots`) so fonts/rendering match.
test.describe('Visual regression', () => {
  test('login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByText('Welcome Back')).toBeVisible()

    await expect(page).toHaveScreenshot('login.png', {
      fullPage: true,
      animations: 'disabled',
      maxDiffPixelRatio: 0.01,
    })
  })
})
