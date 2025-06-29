/**
 * Global teardown for E2E tests
 * Runs after all tests complete
 */

module.exports = async () => {
  console.log('🧹 Cleaning up E2E test environment...');
  
  // Cleanup any temporary files or processes if needed
  // For now, we're not starting/stopping services in the tests
  // so no cleanup is needed
  
  console.log('✅ E2E test cleanup complete');
};