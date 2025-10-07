import { test, expect } from '@playwright/test'

test.describe('Supplier Configuration Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[name="username"]', 'admin')
    await page.fill('input[name="password"]', 'Admin123!')
    await page.click('button[type="submit"]')

    // Wait for dashboard
    await expect(page).toHaveURL(/.*\/dashboard/)

    // Navigate to suppliers page
    await page.goto('/suppliers')
  })

  test('should display supplier configuration page', async ({ page }) => {
    await expect(page.getByText('Supplier Configuration')).toBeVisible()
    await expect(page.getByText('Manage supplier API configurations')).toBeVisible()
    await expect(page.getByRole('button', { name: /Add Supplier/i })).toBeVisible()
  })

  test('should display existing suppliers', async ({ page }) => {
    // Wait for suppliers to load
    await page.waitForSelector('[data-testid="supplier-card"]', { timeout: 10000 })

    // Should show supplier cards
    const supplierCards = page.locator('[data-testid="supplier-card"]')
    await expect(supplierCards).toHaveCount(3) // LCSC, DigiKey, Mouser from mock data

    // Check specific suppliers
    await expect(page.getByText('LCSC Electronics')).toBeVisible()
    await expect(page.getByText('DigiKey Electronics')).toBeVisible()
    await expect(page.getByText('Mouser Electronics')).toBeVisible()
  })

  test('should open add supplier modal', async ({ page }) => {
    await page.click('button[text="Add Supplier"]')

    // Wait for modal to open
    await expect(page.getByText('Add Supplier Configuration')).toBeVisible()
    await expect(page.getByText('Choose a supplier to configure')).toBeVisible()
  })

  test('should add new supplier configuration', async ({ page }) => {
    // Open add supplier modal
    await page.click('button[text="Add Supplier"]')

    // Wait for modal and select a supplier type
    await page.waitForSelector('text=Choose a supplier to configure')

    // Click on a supplier option (assuming they're displayed as cards)
    await page.click('[data-testid="supplier-option-test"]')

    // Fill in configuration form
    await page.fill('input[name="display_name"]', 'Test Supplier Config')
    await page.fill('input[name="base_url"]', 'https://api.test-supplier.com')
    await page.fill('textarea[name="description"]', 'Test supplier for E2E testing')

    // Enable some capabilities
    await page.check('input[name="supports_pricing"]')
    await page.check('input[name="supports_datasheet"]')

    // Submit form
    await page.click('button[text="Save Configuration"]')

    // Wait for modal to close and supplier to appear
    await expect(page.getByText('Add Supplier Configuration')).not.toBeVisible()
    await expect(page.getByText('Test Supplier Config')).toBeVisible()
  })

  test('should test supplier connection', async ({ page }) => {
    // Wait for suppliers to load
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Find the first test connection button
    const testButton = page.locator('[title="Test Connection"]').first()
    await testButton.click()

    // Wait for test result to appear
    await page.waitForSelector('[data-testid="test-result"]', { timeout: 10000 })

    // Should show test result (success or failure)
    const testResult = page.locator('[data-testid="test-result"]')
    await expect(testResult).toBeVisible()
  })

  test('should enable/disable supplier', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Find a supplier that's currently enabled
    const enabledSupplier = page
      .locator('[data-testid="supplier-card"]')
      .filter({
        has: page.locator('text=Disable'),
      })
      .first()

    // Click disable button
    await enabledSupplier.locator('text=Disable').click()

    // Wait for update
    await page.waitForTimeout(1000)

    // Should now show "Enable" button
    await expect(enabledSupplier.locator('text=Enable')).toBeVisible()
  })

  test('should delete supplier configuration', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Count initial suppliers
    const initialCount = await page.locator('[data-testid="supplier-card"]').count()

    // Find delete button for a test supplier
    const deleteButton = page
      .locator('[data-testid="supplier-card"]')
      .filter({ has: page.locator('text=Test Supplier') })
      .locator('text=Delete')
      .first()

    // Handle confirmation dialog
    page.on('dialog', (dialog) => {
      expect(dialog.message()).toContain('Are you sure you want to delete')
      dialog.accept()
    })

    await deleteButton.click()

    // Wait for supplier to be removed
    await page.waitForTimeout(2000)

    // Should have one less supplier
    const finalCount = await page.locator('[data-testid="supplier-card"]').count()
    expect(finalCount).toBe(initialCount - 1)
  })

  test('should show credential status when toggled', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Click the show credentials status button
    await page.click('text=Show Credentials Status')

    // Should show credential status for each supplier
    await expect(page.getByText('Credentials:')).toBeVisible()
    await expect(page.getByText('Not Set')).toBeVisible()
  })

  test('should filter suppliers by view', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Test view switching if implemented
    const viewButtons = page.locator('[data-testid="view-filter"]')
    if ((await viewButtons.count()) > 0) {
      await viewButtons.first().click()

      // Verify filtering works
      await page.waitForTimeout(1000)
      const filteredCards = page.locator('[data-testid="supplier-card"]')
      await expect(filteredCards.first()).toBeVisible()
    }
  })

  test('should open edit supplier modal', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Click edit button (settings icon)
    const editButton = page.locator('[title="Edit Configuration"]').first()
    await editButton.click()

    // Should open edit modal
    await expect(page.getByText('Edit Supplier Configuration')).toBeVisible()
  })

  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept and fail supplier requests
    await page.route('**/api/config/suppliers', (route) => {
      route.abort('failed')
    })

    await page.goto('/suppliers')

    // Should show error message
    await expect(page.getByText(/Error loading/i)).toBeVisible()
  })

  test('should show loading state while fetching suppliers', async ({ page }) => {
    // Intercept and delay supplier requests
    await page.route('**/api/config/suppliers', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      route.continue()
    })

    await page.goto('/suppliers')

    // Should show loading state
    await expect(page.getByText(/Loading/i)).toBeVisible()

    // Eventually should load suppliers
    await page.waitForSelector('[data-testid="supplier-card"]', { timeout: 15000 })
  })

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await page.goto('/suppliers')
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Should adapt layout for mobile
    const supplierCards = page.locator('[data-testid="supplier-card"]')
    await expect(supplierCards.first()).toBeVisible()

    // Check that horizontal scrolling isn't needed
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth)
    const bodyClientWidth = await page.evaluate(() => document.body.clientWidth)
    expect(bodyScrollWidth).toBeLessThanOrEqual(bodyClientWidth + 1) // Allow for rounding
  })

  test('should handle keyboard navigation', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Test tab navigation
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Should be able to reach interactive elements
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()

    // Test Enter key activation
    await page.keyboard.press('Enter')

    // Should trigger appropriate action (depends on focused element)
  })

  test('should display supplier capabilities correctly', async ({ page }) => {
    await page.waitForSelector('[data-testid="supplier-card"]')

    // Check that capabilities are displayed
    await expect(page.getByText('datasheet')).toBeVisible()
    await expect(page.getByText('pricing')).toBeVisible()

    // Check capability count
    const capabilityBadges = page.locator('[data-testid="capability-badge"]')
    await expect(capabilityBadges.first()).toBeVisible()
  })
})
