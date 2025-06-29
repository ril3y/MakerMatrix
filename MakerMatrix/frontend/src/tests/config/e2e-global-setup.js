/**
 * Global setup for E2E tests
 * Runs before all tests start
 */

const { spawn } = require('child_process');
const { promisify } = require('util');
const sleep = promisify(setTimeout);

module.exports = async () => {
  console.log('🚀 Starting E2E test environment...');
  
  // Check if backend and frontend are already running
  const axios = require('axios');
  
  try {
    // Try to reach the API
    await axios.get('https://localhost:8443/api/utility/get_counts', {
      timeout: 5000,
      httpsAgent: new (require('https').Agent)({
        rejectUnauthorized: false
      })
    });
    console.log('✅ Backend is already running');
  } catch (error) {
    console.log('⚠️  Backend not responding, tests may fail');
    console.log('   Please ensure the backend is running on https://localhost:8443');
  }

  try {
    // Try to reach the frontend
    await axios.get('https://localhost:5173', {
      timeout: 5000,
      httpsAgent: new (require('https').Agent)({
        rejectUnauthorized: false
      })
    });
    console.log('✅ Frontend is already running');
  } catch (error) {
    console.log('⚠️  Frontend not responding, tests may fail');
    console.log('   Please ensure the frontend is running on https://localhost:5173');
  }

  console.log('🎯 E2E test environment ready!');
};