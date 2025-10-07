/**
 * UI Test: Import Functionality End-to-End Test
 *
 * This test verifies that the import functionality works correctly
 * with the unified import system and task-based progress tracking.
 */

const puppeteer = require('puppeteer')
const fs = require('fs')
const path = require('path')

describe('Import Functionality UI Test', () => {
  let browser
  let page

  const FRONTEND_URL = 'https://localhost:5173'
  const TEST_CSV_PATH = path.join(
    __dirname,
    '../../../tests/csv_test_data/LCSC_Exported__20241222_232708.csv'
  )

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: false, // Set to true for CI
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'],
    })
    page = await browser.newPage()

    // Log console messages and errors
    page.on('console', (msg) => console.log('PAGE LOG:', msg.text()))
    page.on('pageerror', (error) => console.error('PAGE ERROR:', error.message))
  })

  afterAll(async () => {
    if (browser) {
      await browser.close()
    }
  })

  test('should successfully import CSV file with task-based progress tracking', async () => {
    // Navigate to the frontend
    await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2' })

    // Login
    await page.waitForSelector('input[type="text"]', { timeout: 10000 })
    await page.type('input[type="text"]', 'admin')
    await page.type('input[type="password"]', 'Admin123!')
    await page.click('button[type="submit"]')

    // Wait for dashboard to load
    await page.waitForSelector('.dashboard', { timeout: 10000 })

    // Navigate to import page
    await page.goto(`${FRONTEND_URL}/import`, { waitUntil: 'networkidle2' })

    // Wait for import page to load
    await page.waitForSelector('.import-selector', { timeout: 10000 })

    // Select LCSC importer
    await page.click('button[data-testid="lcsc-importer"]')

    // Wait for file input to appear
    await page.waitForSelector('input[type="file"]', { timeout: 5000 })

    // Upload CSV file
    const fileInput = await page.$('input[type="file"]')
    await fileInput.uploadFile(TEST_CSV_PATH)

    // Wait for file preview to load
    await page.waitForSelector('.file-preview', { timeout: 10000 })

    // Verify file preview shows data
    const previewRows = await page.$$eval('.preview-row', (rows) => rows.length)
    expect(previewRows).toBeGreaterThan(0)

    // Fill in order information
    await page.type('input[name="order_number"]', 'TEST-ORDER-001')
    await page.type('input[name="order_date"]', '2024-01-01')
    await page.type('textarea[name="notes"]', 'UI Test Import')

    // Start import
    await page.click('button[data-testid="import-button"]')

    // Wait for import to start
    await page.waitForSelector('.import-progress', { timeout: 10000 })

    // Monitor progress
    let progressComplete = false
    let attempts = 0
    const maxAttempts = 30 // 30 seconds timeout

    while (!progressComplete && attempts < maxAttempts) {
      await page.waitForTimeout(1000)

      try {
        const progressElement = await page.$('.import-progress')
        if (progressElement) {
          const progressText = await page.evaluate((el) => el.textContent, progressElement)
          console.log('Import progress:', progressText)

          // Check if import is complete
          if (progressText.includes('completed') || progressText.includes('100%')) {
            progressComplete = true
          }
        } else {
          // Progress element disappeared, import might be done
          progressComplete = true
        }
      } catch (error) {
        console.log('Progress check error:', error.message)
        attempts++
      }

      attempts++
    }

    // Verify import completed successfully
    await page.waitForSelector('.import-success', { timeout: 5000 })

    const successMessage = await page.$eval('.import-success', (el) => el.textContent)
    expect(successMessage).toContain('successfully')

    // Verify parts were created
    await page.goto(`${FRONTEND_URL}/parts`, { waitUntil: 'networkidle2' })

    // Wait for parts table to load
    await page.waitForSelector('.parts-table', { timeout: 10000 })

    // Check that parts were imported
    const partRows = await page.$$eval('.parts-table tbody tr', (rows) => rows.length)
    expect(partRows).toBeGreaterThan(0)

    console.log('✅ Import functionality test passed!')
  }, 60000) // 60 second timeout

  test('should handle import errors gracefully', async () => {
    // Navigate to import page
    await page.goto(`${FRONTEND_URL}/import`, { waitUntil: 'networkidle2' })

    // Select LCSC importer
    await page.click('button[data-testid="lcsc-importer"]')

    // Try to import without selecting a file
    await page.click('button[data-testid="import-button"]')

    // Verify error message appears
    await page.waitForSelector('.error-message', { timeout: 5000 })

    const errorMessage = await page.$eval('.error-message', (el) => el.textContent)
    expect(errorMessage).toContain('file')

    console.log('✅ Error handling test passed!')
  })

  test('should show task progress correctly', async () => {
    // This test would verify that the task-based progress tracking works
    // For now, we'll just verify the UI elements exist

    await page.goto(`${FRONTEND_URL}/tasks`, { waitUntil: 'networkidle2' })

    // Wait for tasks page to load
    await page.waitForSelector('.tasks-table', { timeout: 10000 })

    // Check that tasks table exists
    const tasksTable = await page.$('.tasks-table')
    expect(tasksTable).toBeTruthy()

    console.log('✅ Task progress UI test passed!')
  })
})
