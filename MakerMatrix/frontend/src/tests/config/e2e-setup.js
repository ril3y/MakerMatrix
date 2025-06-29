/**
 * E2E Test Setup
 * Global setup for end-to-end tests
 */

const { expect } = require('@jest/globals');

// Global timeout for all E2E tests
jest.setTimeout(60000);

// Setup global variables
global.testConfig = {
  baseURL: process.env.E2E_BASE_URL || 'https://localhost:5173',
  apiURL: process.env.E2E_API_URL || 'https://localhost:8443',
  headless: process.env.CI === 'true',
  slowMo: process.env.E2E_SLOW_MO ? parseInt(process.env.E2E_SLOW_MO) : 0
};

// Extend expect with custom matchers for E2E tests
expect.extend({
  toBeValidSupplierResponse(received) {
    const pass = received && 
                 received.status === 'success' && 
                 received.data && 
                 typeof received.data === 'object';

    if (pass) {
      return {
        message: () => `expected ${received} not to be a valid supplier response`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be a valid supplier response`,
        pass: false,
      };
    }
  }
});

// Global error handler
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Setup test screenshots directory
const fs = require('fs').promises;
const path = require('path');

beforeAll(async () => {
  const screenshotDir = path.join(__dirname, '../../..', 'test-screenshots');
  try {
    await fs.mkdir(screenshotDir, { recursive: true });
  } catch (error) {
    // Directory might already exist
  }
});