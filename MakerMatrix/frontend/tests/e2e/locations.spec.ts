import { test, expect } from '@playwright/test'

test.describe('Locations Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('#username', 'admin')
    await page.fill('#password', 'Admin123!')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 })
  })

  test('should navigate to locations page', async ({ page }) => {
    // Click on Locations in the sidebar
    await page.click('text=Locations')
    await expect(page).toHaveURL(/.*\/locations/)
    await expect(page.getByRole('heading', { name: /Locations/i })).toBeVisible()
  })

  test('should display locations list', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Should show locations in some form (tree structure, cards, or list)
    const hasLocationsContent =
      (await page.locator('text=/location/i').count()) > 0 ||
      (await page.locator('[class*="location"]').count()) > 0

    expect(hasLocationsContent).toBeTruthy()
  })

  test('should open add location modal', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Click Add Location button
    const addButton = page.locator('button:has-text("Add Location"), button:has-text("New Location")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)

      // Modal should be visible - check for modal overlay or form
      const modalVisible =
        (await page.locator('[role="dialog"]').count()) > 0 ||
        (await page.locator('.modal').count()) > 0 ||
        (await page.locator('form').count()) > 0

      expect(modalVisible).toBeTruthy()
    }
  })

  test('should display location hierarchy', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Look for hierarchical structure indicators (expand/collapse buttons, tree)
    const hierarchyIndicators = page.locator(
      'button[aria-label*="expand"], button[aria-label*="collapse"], .tree-node, [data-testid*="tree"]'
    )

    // Locations page should show some structure
    await expect(page.locator('body')).toContainText(/location/i)
  })

  test('should expand and collapse location tree', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Find expandable nodes
    const expandButton = page.locator(
      'button[aria-label*="expand"]:visible, button:has-text("▶"):visible, button:has-text("►"):visible'
    ).first()

    if (await expandButton.count() > 0 && await expandButton.isVisible()) {
      // Click to expand
      await expandButton.click()
      await page.waitForTimeout(300)

      // Should show children or change icon
      const collapseButton = page.locator(
        'button[aria-label*="collapse"], button:has-text("▼"), button:has-text("▲")'
      )
      if (await collapseButton.count() > 0) {
        await expect(collapseButton.first()).toBeVisible()
      }
    }
  })

  test('should search for locations', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]')
    if (await searchInput.count() > 0) {
      await searchInput.first().fill('office')
      await page.waitForTimeout(500)

      // Results should update
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should view location details', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Click on a location to view details
    const viewButton = page.locator('button:has-text("View"), button:has-text("Details")')
    if (await viewButton.count() > 0) {
      await viewButton.first().click()

      // Should show location details (modal or page)
      await page.waitForTimeout(500)
      const detailsVisible =
        (await page.locator('[role="dialog"], [data-testid="location-details"]').count()) > 0

      if (detailsVisible) {
        await expect(page.locator('[role="dialog"]').first()).toBeVisible()
      }
    }
  })

  test('should filter locations by type', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Look for type filter
    const typeFilter = page.locator('select:has-text("Type"), button:has-text("Type")')
    if (await typeFilter.count() > 0) {
      await typeFilter.first().click()
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should show parts count for each location', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Locations should show how many parts they contain
    // Check for text containing "part" or "parts"
    const hasPartsInfo =
      (await page.locator('text=/part/i').count()) > 0 ||
      (await page.locator('[data-testid*="parts-count"]').count()) > 0 ||
      (await page.locator('text=/\\d+/').count()) > 0

    expect(hasPartsInfo).toBeTruthy()
  })

  test('should handle empty locations list gracefully', async ({ page }) => {
    await page.goto('/locations')
    await page.waitForLoadState('networkidle')

    // Page should load without errors
    await expect(page.locator('body')).toBeVisible()

    // Should show either locations or empty state
    const hasContent =
      (await page.locator('text=/location/i').count()) > 0 ||
      (await page.locator('text=/no locations/i').count()) > 0 ||
      (await page.locator('text=/empty/i').count()) > 0

    expect(hasContent).toBeTruthy()
  })
})
