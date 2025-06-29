/**
 * Jest configuration for E2E tests
 */

module.exports = {
  displayName: 'E2E Tests',
  testMatch: ['**/*.e2e.test.js'],
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/src/tests/config/e2e-setup.js'],
  testTimeout: 60000, // 60 seconds for E2E tests
  globalSetup: '<rootDir>/src/tests/config/e2e-global-setup.js',
  globalTeardown: '<rootDir>/src/tests/config/e2e-global-teardown.js',
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/tests/**',
    '!src/**/*.test.{js,jsx}',
    '!src/**/*.e2e.test.{js,jsx}'
  ],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest'
  }
};