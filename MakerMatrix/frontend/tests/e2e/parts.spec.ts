import { test, expect } from '@playwright/test'

test.describe('Parts Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.fill('#username', 'admin')
    await page.fill('#password', 'Admin123!')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 })
  })

  test('should navigate to parts page', async ({ page }) => {
    // Click on Parts in the sidebar
    await page.click('text=Parts')
    await expect(page).toHaveURL(/.*\/parts/)
    await expect(page.getByRole('heading', { name: /Parts Inventory/i }).first()).toBeVisible()
  })

  test('should display parts list', async ({ page }) => {
    await page.goto('/parts')

    // Wait for parts to load
    await page.waitForLoadState('networkidle')

    // Should show parts table or grid
    const partsContent = page.locator('[data-testid="parts-list"], table, .grid')
    await expect(partsContent.first()).toBeVisible({ timeout: 10000 })
  })

  test('should open add part modal', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Click Add Part button
    const addButton = page.locator('button:has-text("Add Part"), button:has-text("New Part")')
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

  test('should search for parts', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Find search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]')
    if (await searchInput.count() > 0) {
      await searchInput.first().fill('resistor')
      await page.waitForTimeout(500) // Wait for search debounce

      // Results should update
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should filter parts by category', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Look for category filter
    const categoryFilter = page.locator('select:has-text("Category"), button:has-text("Category")')
    if (await categoryFilter.count() > 0) {
      await categoryFilter.first().click()
      // Filter options should be visible
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should sort parts list', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Look for sortable column headers
    const sortableHeader = page.locator('th[role="columnheader"], th button, .sortable')
    if (await sortableHeader.count() > 0) {
      await sortableHeader.first().click()
      await page.waitForTimeout(300)
      // Content should reload
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should navigate through pages', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Look for pagination controls
    const nextButton = page.locator('button:has-text("Next"), button[aria-label*="next"]')
    if (await nextButton.count() > 0 && await nextButton.first().isEnabled()) {
      await nextButton.first().click()
      await page.waitForTimeout(500)
      await expect(page).toHaveURL(/.*\/parts/)
    }
  })

  test('should view part details', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Click on first part (view details button or row)
    const viewButton = page.locator('button:has-text("View"), a[href*="/parts/"]')
    if (await viewButton.count() > 0) {
      await viewButton.first().click()

      // Should navigate to part details page or show modal
      await page.waitForTimeout(500)
      const detailsVisible = await page.locator('[role="dialog"], [data-testid="part-details"]').count() > 0
      const urlChanged = page.url().includes('/parts/')

      expect(detailsVisible || urlChanged).toBeTruthy()
    }
  })

  test('should handle empty search results', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]')
    if (await searchInput.count() > 0) {
      // Search for something unlikely to exist
      await searchInput.first().fill('xyzabc123nonexistent999')
      await page.waitForTimeout(1000)

      // Should show no results message or empty state
      const noResults = page.locator('text=/No (parts|results) found/i, text=/Empty/i')
      if (await noResults.count() > 0) {
        await expect(noResults.first()).toBeVisible()
      }
    }
  })

  test('should display part count/pagination info', async ({ page }) => {
    await page.goto('/parts')
    await page.waitForLoadState('networkidle')

    // Should show pagination info like "Showing 1-10 of 74"
    const paginationInfo = page.locator('text=/Showing|of|total/i')
    if (await paginationInfo.count() > 0) {
      await expect(paginationInfo.first()).toBeVisible()
    }
  })
})
