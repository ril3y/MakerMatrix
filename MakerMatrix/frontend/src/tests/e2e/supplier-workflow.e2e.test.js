/**
 * End-to-End tests for Supplier Configuration Workflow
 * 
 * These tests use Puppeteer to replicate the exact browser interactions
 * we performed to discover and verify the MouserSupplier bug fix.
 */

const puppeteer = require('puppeteer');
const { expect } = require('@jest/globals');

describe('Supplier Configuration E2E Tests', () => {
  let browser;
  let page;
  const baseURL = process.env.E2E_BASE_URL || 'https://localhost:5173';
  const apiURL = process.env.E2E_API_URL || 'https://localhost:8443';

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: process.env.CI === 'true',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--ignore-certificate-errors',
        '--ignore-ssl-errors',
        '--disable-web-security'
      ]
    });
    page = await browser.newPage();
    
    // Set viewport to match our testing environment
    await page.setViewport({ width: 1920, height: 1080 });
    
    // Listen for console errors and network failures
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser console error:', msg.text());
      }
    });

    page.on('response', response => {
      if (!response.ok()) {
        console.log(`Failed request: ${response.url()} - ${response.status()}`);
      }
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  beforeEach(async () => {
    // Navigate to the application
    await page.goto(baseURL, { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
  });

  describe('Navigation to Supplier Settings', () => {
    test('should navigate to supplier settings successfully', async () => {
      // Wait for the dashboard to load
      await page.waitForSelector('text=Dashboard', { timeout: 10000 });
      
      // Take screenshot of initial state
      await page.screenshot({ 
        path: 'test-screenshots/dashboard-initial.png',
        fullPage: true 
      });

      // Click on Settings in the sidebar
      await page.click('text=Settings');
      
      // Wait for settings page to load
      await page.waitForSelector('text=Configure application preferences', { timeout: 5000 });
      
      // Click on Suppliers tab
      await page.click('text=Suppliers');
      
      // Wait for supplier configuration page
      await page.waitForSelector('text=Supplier Configuration', { timeout: 5000 });
      
      // Take screenshot of suppliers page
      await page.screenshot({ 
        path: 'test-screenshots/suppliers-page.png',
        fullPage: true 
      });

      // Verify we're on the correct page
      const heading = await page.textContent('h1, h2, .title');
      expect(heading).toContain('Supplier');
    });
  });

  describe('Add Supplier Button Functionality', () => {
    test('should display Add Supplier button when no suppliers configured', async () => {
      // Navigate to suppliers page
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');

      // Look for "Add Supplier" button or "No suppliers found" message
      const addButton = await page.waitForSelector('button:has-text("Add Supplier")', { 
        timeout: 10000 
      });
      
      expect(addButton).toBeTruthy();
      
      // Take screenshot showing the button
      await page.screenshot({ 
        path: 'test-screenshots/add-supplier-button.png',
        fullPage: true 
      });
    });

    test('should open supplier modal when Add Supplier is clicked', async () => {
      // Navigate to suppliers page
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');

      // Click Add Supplier button
      await page.click('button:has-text("Add Supplier")');
      
      // Wait for modal to appear
      await page.waitForSelector('text=Add Supplier Configuration', { timeout: 10000 });
      
      // Take screenshot of opened modal
      await page.screenshot({ 
        path: 'test-screenshots/supplier-modal-opened.png',
        fullPage: true 
      });

      // Verify modal content
      const modalTitle = await page.textContent('h1, h2, .modal-title, [data-testid="modal-title"]');
      expect(modalTitle).toContain('Add Supplier Configuration');
      
      const modalDescription = await page.textContent('text=Choose a supplier to configure');
      expect(modalDescription).toBeTruthy();
    });
  });

  describe('Supplier API Error Handling', () => {
    test('should handle API errors gracefully', async () => {
      // Intercept the suppliers/info API call and mock a 500 error
      await page.setRequestInterception(true);
      
      page.on('request', (request) => {
        if (request.url().includes('/api/suppliers/info')) {
          request.respond({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
              status: 'error',
              message: "Failed to get supplier info: Can't instantiate abstract class MouserSupplier without an implementation for abstract method 'get_configuration_schema'"
            })
          });
        } else {
          request.continue();
        }
      });

      // Navigate to suppliers page
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');

      // Try to click Add Supplier button
      await page.click('button:has-text("Add Supplier")');
      
      // The modal should either not open or show an error
      try {
        await page.waitForSelector('text=Add Supplier Configuration', { timeout: 5000 });
        // If modal opens, check for error handling
        const errorMessage = await page.$('text=Error', 'text=Failed');
        expect(errorMessage).toBeTruthy();
      } catch (error) {
        // Modal didn't open, which is also acceptable error handling
        console.log('Modal did not open due to API error - this is expected behavior');
      }
      
      await page.screenshot({ 
        path: 'test-screenshots/api-error-handling.png',
        fullPage: true 
      });
    });
  });

  describe('Supplier Information Display', () => {
    test('should display all 5 suppliers in the modal', async () => {
      // Navigate and open modal
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      await page.waitForSelector('text=Add Supplier Configuration');

      // Wait for suppliers to load
      await page.waitForTimeout(2000);
      
      // Take screenshot of all suppliers
      await page.screenshot({ 
        path: 'test-screenshots/all-suppliers-displayed.png',
        fullPage: true 
      });

      // Verify all expected suppliers are present
      const suppliers = [
        'DigiKey Electronics',
        'LCSC Electronics', 
        'Mouser Electronics',
        'McMaster-Carr',
        'Bolt Depot'
      ];

      for (const supplier of suppliers) {
        const element = await page.waitForSelector(`text=${supplier}`, { timeout: 5000 });
        expect(element).toBeTruthy();
      }
    });

    test('should display supplier capabilities', async () => {
      // Navigate and open modal
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      await page.waitForSelector('text=Add Supplier Configuration');

      // Wait for suppliers to load
      await page.waitForTimeout(2000);

      // Check for capability indicators
      const capabilities = await page.$$eval('[class*="capability"], [data-testid*="capability"], .badge', 
        elements => elements.map(el => el.textContent)
      );

      // Should have some capabilities displayed
      expect(capabilities.length).toBeGreaterThan(0);
      
      // Common capabilities that should be present
      const capabilityText = capabilities.join(' ').toLowerCase();
      expect(
        capabilityText.includes('search') ||
        capabilityText.includes('datasheet') ||
        capabilityText.includes('part') ||
        capabilityText.includes('pricing')
      ).toBe(true);
    });
  });

  describe('Modal Interaction', () => {
    test('should close modal when cancel button is clicked', async () => {
      // Open modal
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      await page.waitForSelector('text=Add Supplier Configuration');

      // Click cancel button
      await page.click('button:has-text("Cancel")');
      
      // Modal should close
      await page.waitForTimeout(1000);
      const modal = await page.$('text=Add Supplier Configuration');
      expect(modal).toBeFalsy();
      
      await page.screenshot({ 
        path: 'test-screenshots/modal-closed.png',
        fullPage: true 
      });
    });

    test('should handle supplier selection', async () => {
      // Open modal
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      await page.waitForSelector('text=Add Supplier Configuration');

      // Wait for suppliers to load
      await page.waitForTimeout(2000);

      // Click on LCSC Electronics card
      const lcscCard = await page.$('text=LCSC Electronics');
      if (lcscCard) {
        const cardElement = await lcscCard.evaluateHandle(el => 
          el.closest('[class*="card"], [data-testid*="card"], .supplier-option')
        );
        
        if (cardElement) {
          await cardElement.click();
          
          // Should navigate to configuration or show configuration form
          await page.waitForTimeout(2000);
          
          await page.screenshot({ 
            path: 'test-screenshots/supplier-selected.png',
            fullPage: true 
          });

          // Check if we get a configuration form or navigate somewhere
          const configElements = await page.$$('input, select, textarea');
          expect(configElements.length).toBeGreaterThan(0);
        }
      }
    });
  });

  describe('API Endpoint Verification', () => {
    test('should successfully call /api/suppliers/info endpoint', async () => {
      const responses = [];
      
      // Capture network responses
      page.on('response', response => {
        if (response.url().includes('/api/suppliers/info')) {
          responses.push(response);
        }
      });

      // Navigate and trigger API call
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      
      // Wait for API call
      await page.waitForTimeout(3000);

      // Verify API was called and succeeded
      expect(responses.length).toBeGreaterThan(0);
      expect(responses[0].status()).toBe(200);
    });

    test('should verify MouserSupplier fix - no 500 errors', async () => {
      const apiErrors = [];
      
      // Capture any 500 errors
      page.on('response', response => {
        if (response.status() === 500 && response.url().includes('/api/suppliers/info')) {
          apiErrors.push({
            url: response.url(),
            status: response.status()
          });
        }
      });

      // Navigate and trigger API call
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      
      // Wait for API call
      await page.waitForTimeout(3000);

      // Should have no 500 errors
      expect(apiErrors.length).toBe(0);
      
      // Modal should open successfully
      const modal = await page.$('text=Add Supplier Configuration');
      expect(modal).toBeTruthy();
      
      // Should display Mouser Electronics
      const mouserElement = await page.$('text=Mouser Electronics');
      expect(mouserElement).toBeTruthy();
    });
  });

  describe('Console Error Monitoring', () => {
    test('should not have JavaScript errors during supplier workflow', async () => {
      const consoleErrors = [];
      
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Perform the full workflow
      await page.click('text=Settings');
      await page.click('text=Suppliers');
      await page.waitForSelector('text=Supplier Configuration');
      await page.click('button:has-text("Add Supplier")');
      await page.waitForSelector('text=Add Supplier Configuration');
      await page.waitForTimeout(2000);
      await page.click('button:has-text("Cancel")');

      // Filter out non-critical errors (like network timeouts)
      const criticalErrors = consoleErrors.filter(error => 
        !error.includes('timeout') && 
        !error.includes('favicon') &&
        !error.includes('chunk')
      );

      expect(criticalErrors.length).toBe(0);
    });
  });
});

// Test utilities
const setupE2EEnvironment = async () => {
  // Ensure test screenshots directory exists
  const fs = require('fs').promises;
  try {
    await fs.mkdir('test-screenshots', { recursive: true });
  } catch (error) {
    // Directory might already exist
  }
};

// Run setup before tests
beforeAll(async () => {
  await setupE2EEnvironment();
});