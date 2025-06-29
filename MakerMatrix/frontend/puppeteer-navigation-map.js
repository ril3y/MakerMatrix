/**
 * Puppeteer Navigation Map for MakerMatrix
 * 
 * This file provides a centralized mapping of UI elements and navigation patterns
 * to make Puppeteer automation more reliable and maintainable.
 */

const NavigationMap = {
  // Main navigation selectors
  navigation: {
    settings: {
      selectors: [
        'a[href="/settings"]',
        'a[href="#/settings"]',
        'button:has-text("Settings")',
        'nav a:contains("Settings")',
        '[data-testid="settings-nav"]',
        '.nav-item:contains("Settings")'
      ],
      fallback: () => {
        // Look for settings icon (gear, cog, etc.)
        const settingsIcons = document.querySelectorAll('[data-icon="settings"], [class*="settings"], [class*="gear"], [class*="cog"]');
        return settingsIcons[0]?.closest('a, button');
      }
    },
    suppliers: {
      selectors: [
        'a[href="/suppliers"]',
        'a[href="#/suppliers"]',
        'button:has-text("Suppliers")',
        'nav a:contains("Suppliers")',
        '[data-testid="suppliers-nav"]',
        '.nav-item:contains("Suppliers")'
      ]
    },
    dashboard: {
      selectors: [
        'a[href="/"]',
        'a[href="/dashboard"]',
        'button:has-text("Dashboard")',
        'nav a:contains("Dashboard")',
        '[data-testid="dashboard-nav"]'
      ]
    }
  },

  // Supplier page elements
  suppliers: {
    addSupplierButton: {
      selectors: [
        'button:has-text("Add Supplier")',
        '[data-testid="add-supplier-button"]',
        'button:contains("Add Supplier")',
        '.add-supplier-btn',
        'button[class*="add"][class*="supplier"]'
      ]
    },
    supplierCards: {
      lcsc: {
        selectors: [
          'button:has-text("LCSC Electronics")',
          '[data-supplier="lcsc"]',
          '.supplier-card:has-text("LCSC")',
          'button:contains("LCSC Electronics")',
          '[data-testid="supplier-lcsc"]'
        ]
      },
      digikey: {
        selectors: [
          'button:has-text("DigiKey")',
          '[data-supplier="digikey"]',
          '.supplier-card:has-text("DigiKey")',
          'button:contains("DigiKey")',
          '[data-testid="supplier-digikey"]'
        ]
      },
      mouser: {
        selectors: [
          'button:has-text("Mouser Electronics")',
          '[data-supplier="mouser"]',
          '.supplier-card:has-text("Mouser")',
          'button:contains("Mouser Electronics")',
          '[data-testid="supplier-mouser"]'
        ]
      }
    },
    testConnectionButton: {
      selectors: [
        'button:has-text("Test Connection")',
        '[data-testid="test-connection-button"]',
        'button:contains("Test Connection")',
        '.test-connection-btn',
        'button[class*="test"][class*="connection"]'
      ]
    },
    saveConfigButton: {
      selectors: [
        'button:has-text("Save Configuration")',
        'button:has-text("Save")',
        '[data-testid="save-config-button"]',
        'button:contains("Save Configuration")',
        '.save-config-btn'
      ]
    }
  },

  // Modal elements
  modals: {
    closeButton: {
      selectors: [
        'button[aria-label="Close"]',
        '.modal-close',
        '[data-testid="modal-close"]',
        'button:has-text("×")',
        'button:has-text("Close")'
      ]
    }
  }
};

/**
 * Helper functions for navigation
 */
const NavigationHelpers = {
  /**
   * Find element using multiple selector strategies
   * @param {Page} page - Puppeteer page object
   * @param {Array} selectors - Array of CSS selectors to try
   * @param {Function} fallback - Optional fallback function
   * @returns {Promise<ElementHandle|null>}
   */
  async findElement(page, selectors, fallback = null) {
    // Try each selector
    for (const selector of selectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          console.log(`Found element with selector: ${selector}`);
          return element;
        }
      } catch (error) {
        console.log(`Selector failed: ${selector} - ${error.message}`);
      }
    }

    // Try text-based selectors
    for (const selector of selectors) {
      if (selector.includes(':has-text') || selector.includes(':contains')) {
        try {
          // Convert to XPath for text matching
          const text = selector.match(/["'](.*?)["']/)?.[1];
          if (text) {
            const xpath = `//*[contains(text(), "${text}")]`;
            const elements = await page.$x(xpath);
            if (elements.length > 0) {
              console.log(`Found element with XPath: ${xpath}`);
              return elements[0];
            }
          }
        } catch (error) {
          console.log(`XPath failed for: ${selector} - ${error.message}`);
        }
      }
    }

    // Try fallback function if provided
    if (fallback) {
      try {
        const result = await page.evaluate(fallback);
        if (result) {
          console.log('Found element using fallback function');
          return result;
        }
      } catch (error) {
        console.log(`Fallback function failed: ${error.message}`);
      }
    }

    console.log('Element not found with any selector');
    return null;
  },

  /**
   * Navigate to settings page
   * @param {Page} page - Puppeteer page object
   * @returns {Promise<boolean>}
   */
  async goToSettings(page) {
    const element = await this.findElement(
      page, 
      NavigationMap.navigation.settings.selectors,
      NavigationMap.navigation.settings.fallback
    );
    
    if (element) {
      await element.click();
      await page.waitForNavigation({ waitUntil: 'networkidle0' });
      return true;
    }
    return false;
  },

  /**
   * Navigate to suppliers page
   * @param {Page} page - Puppeteer page object
   * @returns {Promise<boolean>}
   */
  async goToSuppliers(page) {
    const element = await this.findElement(
      page, 
      NavigationMap.navigation.suppliers.selectors
    );
    
    if (element) {
      await element.click();
      await page.waitForNavigation({ waitUntil: 'networkidle0' });
      return true;
    }
    return false;
  },

  /**
   * Click Add Supplier button
   * @param {Page} page - Puppeteer page object
   * @returns {Promise<boolean>}
   */
  async clickAddSupplier(page) {
    const element = await this.findElement(
      page, 
      NavigationMap.suppliers.addSupplierButton.selectors
    );
    
    if (element) {
      await element.click();
      await page.waitForTimeout(1000); // Wait for modal to open
      return true;
    }
    return false;
  },

  /**
   * Select a supplier from the modal
   * @param {Page} page - Puppeteer page object
   * @param {string} supplierName - Name of supplier (lcsc, digikey, mouser, etc.)
   * @returns {Promise<boolean>}
   */
  async selectSupplier(page, supplierName) {
    const supplierConfig = NavigationMap.suppliers.supplierCards[supplierName.toLowerCase()];
    if (!supplierConfig) {
      console.log(`Supplier ${supplierName} not found in navigation map`);
      return false;
    }

    const element = await this.findElement(page, supplierConfig.selectors);
    
    if (element) {
      await element.click();
      await page.waitForTimeout(1000); // Wait for configuration form to load
      return true;
    }
    return false;
  },

  /**
   * Click Test Connection button
   * @param {Page} page - Puppeteer page object
   * @returns {Promise<boolean>}
   */
  async clickTestConnection(page) {
    const element = await this.findElement(
      page, 
      NavigationMap.suppliers.testConnectionButton.selectors
    );
    
    if (element) {
      await element.click();
      return true;
    }
    return false;
  },

  /**
   * Click Save Configuration button
   * @param {Page} page - Puppeteer page object
   * @returns {Promise<boolean>}
   */
  async clickSaveConfig(page) {
    const element = await this.findElement(
      page, 
      NavigationMap.suppliers.saveConfigButton.selectors
    );
    
    if (element) {
      await element.click();
      return true;
    }
    return false;
  },

  /**
   * Complete supplier configuration workflow
   * @param {Page} page - Puppeteer page object
   * @param {string} supplierName - Name of supplier to configure
   * @returns {Promise<boolean>}
   */
  async completeSupplierWorkflow(page, supplierName) {
    console.log(`Starting supplier configuration workflow for: ${supplierName}`);
    
    // Step 1: Navigate to suppliers page (try both direct and via settings)
    let success = await this.goToSuppliers(page);
    if (!success) {
      console.log('Direct navigation to suppliers failed, trying via settings...');
      success = await this.goToSettings(page);
      if (success) {
        success = await this.goToSuppliers(page);
      }
    }
    
    if (!success) {
      console.log('Failed to navigate to suppliers page');
      return false;
    }

    // Step 2: Click Add Supplier
    success = await this.clickAddSupplier(page);
    if (!success) {
      console.log('Failed to click Add Supplier button');
      return false;
    }

    // Step 3: Select the supplier
    success = await this.selectSupplier(page, supplierName);
    if (!success) {
      console.log(`Failed to select supplier: ${supplierName}`);
      return false;
    }

    // Step 4: Test connection
    success = await this.clickTestConnection(page);
    if (!success) {
      console.log('Failed to click Test Connection button');
      return false;
    }

    // Wait for test to complete
    await page.waitForTimeout(3000);

    // Step 5: Save configuration
    success = await this.clickSaveConfig(page);
    if (!success) {
      console.log('Failed to click Save Configuration button');
      return false;
    }

    console.log(`Successfully completed supplier configuration workflow for: ${supplierName}`);
    return true;
  }
};

module.exports = { NavigationMap, NavigationHelpers };