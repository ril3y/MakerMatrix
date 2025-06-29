# Supplier Configuration Tests

This directory contains comprehensive tests for the supplier configuration functionality, specifically designed to prevent and detect issues like the MouserSupplier configuration schema bug.

## Test Structure

### Integration Tests (`integration/`)
- **supplier-configuration.test.js**: React Testing Library tests that simulate user interactions with the supplier configuration components
- Tests modal opening, API error handling, supplier display, and user workflows

### E2E Tests (`e2e/`)
- **supplier-workflow.e2e.test.js**: Puppeteer-based end-to-end tests that replicate the exact browser interactions performed during manual testing
- Tests the complete user journey from navigation to supplier selection

### Configuration (`config/`)
- Jest configuration files for E2E test setup and teardown
- Global test utilities and custom matchers

## The Bug We're Testing For

These tests specifically address the bug discovered on 2025-06-28:

**Issue**: The `MouserSupplier` class was missing the required abstract method `get_configuration_schema()`, causing a 500 Internal Server Error when the frontend tried to load supplier information.

**Error Message**: 
```
"Failed to get supplier info: Can't instantiate abstract class MouserSupplier without an implementation for abstract method 'get_configuration_schema'"
```

**Fix Applied**: Added the missing `get_configuration_schema()` method to `/home/ril3y/MakerMatrix/MakerMatrix/suppliers/mouser.py`

## Test Scenarios

### 1. API Error Handling
- Tests that verify the frontend gracefully handles 500 errors from `/api/suppliers/info`
- Ensures the UI doesn't crash when supplier instantiation fails
- Validates error messages are displayed appropriately

### 2. Successful Workflow
- Tests the complete "Add Supplier" workflow when all APIs work correctly
- Verifies all 5 suppliers (DigiKey, LCSC, Mouser, McMaster-Carr, Bolt Depot) are displayed
- Ensures supplier capabilities and information are shown correctly

### 3. Modal Interaction
- Tests opening and closing the supplier selection modal
- Validates supplier selection functionality
- Ensures proper navigation to configuration forms

### 4. Network Monitoring
- Monitors browser console for JavaScript errors
- Tracks API response codes to catch 500 errors
- Verifies no critical errors occur during the workflow

## Running the Tests

### Prerequisites
Ensure both backend and frontend are running:
```bash
# Backend (from project root)
python -m MakerMatrix.main

# Frontend (from frontend directory)
npm run dev
```

### Integration Tests
```bash
# Run React Testing Library tests
npm run test:supplier

# Run with coverage
npm run test:supplier -- --coverage
```

### E2E Tests
```bash
# Run Puppeteer E2E tests
npm run test:supplier:e2e

# Run with visible browser (for debugging)
E2E_HEADLESS=false npm run test:supplier:e2e
```

### All Supplier Tests
```bash
# Run both integration and E2E tests
npm run test:supplier:all
```

## Test Environment Variables

- `E2E_BASE_URL`: Frontend URL (default: https://localhost:5173)
- `E2E_API_URL`: Backend API URL (default: https://localhost:8443)
- `E2E_HEADLESS`: Run browser in headless mode (default: true in CI)
- `E2E_SLOW_MO`: Add delay between actions for debugging (default: 0)

## Test Output

### Screenshots
E2E tests automatically capture screenshots saved to `test-screenshots/`:
- `dashboard-initial.png`: Initial dashboard state
- `suppliers-page.png`: Supplier configuration page
- `add-supplier-button.png`: Page showing the Add Supplier button
- `supplier-modal-opened.png`: Modal with all suppliers displayed
- `api-error-handling.png`: Error state when API fails
- `all-suppliers-displayed.png`: All 5 suppliers in the modal
- `modal-closed.png`: State after closing the modal
- `supplier-selected.png`: Configuration form after selecting a supplier

### Console Output
Tests provide detailed logging:
- API request/response monitoring
- Browser console error tracking
- Step-by-step test execution details

## Development Workflow

### Adding New Supplier Tests
1. Add test cases to `supplier-configuration.test.js` for React component testing
2. Add E2E scenarios to `supplier-workflow.e2e.test.js` for browser automation
3. Update screenshots and expected outcomes

### Debugging Test Failures
1. Check `test-screenshots/` for visual debugging
2. Review browser console errors in test output
3. Use `E2E_HEADLESS=false` to see browser interactions
4. Check API logs in `dev_manager.log` for backend issues

### Continuous Integration
Tests are designed to run in CI environments:
- Use headless mode by default
- Provide clear error messages and screenshots
- Have reasonable timeouts for network operations
- Skip tests if services are not available

## Test Maintenance

### When to Update Tests
- When adding new suppliers to the system
- When changing the supplier configuration UI
- When modifying the `/api/suppliers/info` endpoint
- After fixing supplier-related bugs

### Test Dependencies
- Keep dependencies updated for security
- Ensure Puppeteer version matches Chrome/Chromium in CI
- Update selectors if UI components change
- Maintain compatibility with React Testing Library versions

## Related Files

### Frontend Components
- `src/pages/Settings.tsx`: Main settings page with supplier tab
- `src/components/SupplierModal.tsx`: Add supplier modal component
- `src/services/supplierService.ts`: API service for supplier operations

### Backend Implementation
- `MakerMatrix/suppliers/mouser.py`: Fixed MouserSupplier implementation
- `MakerMatrix/routers/supplier_routes.py`: API routes for supplier operations
- `MakerMatrix/suppliers/base.py`: Abstract base class with required methods

### Test Configuration
- `jest.e2e.config.js`: Jest configuration for E2E tests
- `babel.config.js`: Babel configuration for JSX/ES6 support
- `package.json`: Test scripts and dependencies

## Contributing

When modifying supplier functionality:
1. Run existing tests to ensure no regressions
2. Add new test cases for new features
3. Update documentation if test procedures change
4. Include screenshot updates if UI changes significantly

## Troubleshooting

### Common Issues

**Tests fail with "supplier modal not found"**
- Ensure frontend is running on expected port
- Check if supplier data is loading correctly
- Verify API endpoints are responding

**E2E tests timeout**
- Increase timeout in jest.e2e.config.js
- Check if services are running and responsive
- Look for network connectivity issues

**Integration tests fail**
- Verify React Testing Library setup
- Check mock configurations for API calls
- Ensure component imports are correct

**Screenshots not generated**
- Check write permissions in test-screenshots directory
- Verify Puppeteer has access to create files
- Ensure headless mode is working correctly