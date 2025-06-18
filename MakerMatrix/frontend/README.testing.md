# MakerMatrix Frontend Testing Guide

## Overview

This document provides instructions for running the comprehensive test suite for the MakerMatrix frontend application.

## Test Types

### 1. Unit Tests
- **Framework**: Vitest + React Testing Library
- **Coverage**: Individual components, hooks, services, utilities
- **Command**: `npm run test`
- **Location**: `src/**/*.test.{ts,tsx}`

### 2. Integration Tests
- **Framework**: Vitest + React Testing Library + MSW
- **Coverage**: Component interactions, API integration, form workflows
- **Command**: `npm run test` (included with unit tests)
- **Location**: `src/**/*.test.{ts,tsx}`

### 3. End-to-End Tests
- **Framework**: Playwright
- **Coverage**: Complete user workflows across the entire application
- **Command**: `npm run test:e2e`
- **Location**: `tests/e2e/**/*.spec.ts`

### 4. Visual Regression Tests
- **Framework**: Playwright with visual comparisons
- **Coverage**: UI consistency across themes and screen sizes
- **Command**: `npm run test:visual`
- **Location**: `tests/visual/**/*.spec.ts`

### 5. Accessibility Tests
- **Framework**: Playwright + axe-core
- **Coverage**: WCAG 2.1 AA compliance
- **Command**: Built into E2E tests with `--grep accessibility`

## Quick Start

### Install Dependencies
```bash
cd MakerMatrix/frontend
npm install
```

### Install Playwright Browsers
```bash
npx playwright install
```

### Run All Tests
```bash
# Using the comprehensive test runner
python ../../run-frontend-tests.py --all

# Or individual test types
npm run test:run        # Unit tests
npm run test:e2e       # E2E tests
npm run test:visual    # Visual tests
```

## Test Commands

### Development Commands
```bash
npm run test           # Run tests in watch mode
npm run test:ui        # Run tests with UI interface
npm run test:coverage  # Run tests with coverage report
```

### CI/CD Commands
```bash
npm run test:run       # Run tests once (for CI)
npm run test:e2e       # Run E2E tests
npm run test:all       # Run all test types
```

### Coverage Commands
```bash
npm run test:coverage  # Generate coverage report
open coverage/index.html  # View coverage report
```

## Test Structure

```
MakerMatrix/frontend/
├── src/
│   ├── __tests__/              # Test utilities and setup
│   │   ├── setup.ts           # Test environment setup
│   │   ├── mocks/             # MSW API mocks
│   │   └── utils/             # Test helper functions
│   ├── components/
│   │   └── **/*.test.tsx      # Component tests
│   ├── services/
│   │   └── **/*.test.ts       # Service tests
│   └── hooks/
│       └── **/*.test.ts       # Hook tests
├── tests/
│   ├── e2e/                   # End-to-end tests
│   │   ├── auth.spec.ts
│   │   ├── suppliers.spec.ts
│   │   └── ...
│   └── visual/                # Visual regression tests
├── vitest.config.ts           # Vitest configuration
├── playwright.config.ts       # Playwright configuration
└── package.json              # Scripts and dependencies
```

## Writing Tests

### Unit Test Example
```typescript
// src/components/ui/Modal.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../__tests__/utils/render'
import { setupUser } from '../../__tests__/utils/test-utils'
import { Modal } from './Modal'

describe('Modal', () => {
  it('renders modal when open', () => {
    render(<Modal isOpen={true} onClose={vi.fn()} title="Test">Content</Modal>)
    
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
```

### E2E Test Example
```typescript
// tests/e2e/auth.spec.ts
import { test, expect } from '@playwright/test'

test('should login with valid credentials', async ({ page }) => {
  await page.goto('/login')
  
  await page.fill('input[name="username"]', 'admin')
  await page.fill('input[name="password"]', 'Admin123!')
  await page.click('button[type="submit"]')
  
  await expect(page).toHaveURL(/.*\/dashboard/)
})
```

### API Mocking
```typescript
// src/__tests__/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/parts/get_all_parts', () => {
    return HttpResponse.json({
      status: 'success',
      data: [/* mock parts data */]
    })
  })
]
```

## Test Data Management

### Mock Data Factories
```typescript
// src/__tests__/utils/test-utils.ts
export const createMockPart = (overrides = {}) => ({
  id: 'test-part-1',
  part_name: 'Test Resistor',
  part_number: 'R001',
  // ... other fields
  ...overrides,
})
```

### Using Test Data
```typescript
const mockPart = createMockPart({
  part_name: 'Custom Part Name',
  quantity: 100
})
```

## Coverage Goals

- **Unit Tests**: 90%+ coverage for utilities, hooks, services
- **Component Tests**: 85%+ coverage for all components
- **Integration Tests**: All critical user workflows
- **E2E Tests**: All main application features

## Running with Backend

### Using the Test Runner Script
```bash
# The script automatically manages backend/frontend servers
python ../../run-frontend-tests.py --all
```

### Manual Setup
```bash
# Terminal 1: Start backend
cd ../..
source venv_test/bin/activate
python -m uvicorn MakerMatrix.main:app --host 0.0.0.0 --port 57891

# Terminal 2: Start frontend
cd MakerMatrix/frontend
npm run dev

# Terminal 3: Run tests
npm run test:e2e
```

### Using dev_manager.py
```bash
# Alternative: Use the dev manager
cd ../..
python dev_manager.py
# Press '5' to start both servers
# Press 'q' to quit when done

# Then run tests in another terminal
cd MakerMatrix/frontend
npm run test:e2e
```

## Debugging Tests

### Unit Test Debugging
```bash
# Run tests in debug mode
npm run test:ui

# Run specific test file
npx vitest src/components/ui/Modal.test.tsx

# Run tests with verbose output
npx vitest --reporter=verbose
```

### E2E Test Debugging
```bash
# Run E2E tests in headed mode (see browser)
npm run test:e2e:headed

# Run specific E2E test
npx playwright test tests/e2e/auth.spec.ts

# Debug mode with browser inspector
npx playwright test --debug
```

### Visual Test Debugging
```bash
# Update visual baselines
npx playwright test tests/visual --update-snapshots

# Show visual diff report
npx playwright show-report
```

## CI/CD Integration

### GitHub Actions
Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Changes to frontend code

### Local Pre-commit
```bash
# Run before committing
npm run test:run
npm run lint
npm run build
```

## Performance Monitoring

### Bundle Size Analysis
```bash
npm run build
npx bundlesize
```

### Lighthouse Testing
```bash
npm install -g @lhci/cli
lhci autorun
```

## Troubleshooting

### Common Issues

1. **Tests timeout**: Increase timeout in test files or configuration
2. **MSW not working**: Check if `src/__tests__/setup.ts` is properly configured
3. **Playwright browser issues**: Run `npx playwright install`
4. **Backend not starting**: Check if `venv_test` exists and has dependencies

### Environment Issues
```bash
# Reset node_modules
rm -rf node_modules package-lock.json
npm install

# Reset Playwright
npx playwright install --force

# Reset Python environment
rm -rf ../../venv_test
python -m venv ../../venv_test
source ../../venv_test/bin/activate
pip install -r ../../requirements.txt
```

### Debug Configuration
```bash
# Enable verbose logging
DEBUG=pw:api npm run test:e2e

# Run with trace
npx playwright test --trace on
```

## Best Practices

### Test Organization
- Group related tests in `describe` blocks
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Test behavior, not implementation

### Test Data
- Use factory functions for consistent test data
- Avoid hardcoded values
- Clean up test data between tests

### Assertions
- Use specific assertions (`toHaveTextContent` vs `toContain`)
- Test accessibility attributes
- Verify user interactions work correctly

### Performance
- Use `screen.getByRole` over `container.querySelector`
- Avoid unnecessary test isolation
- Mock external dependencies

## Contributing

### Adding New Tests
1. Create test file alongside the component/service
2. Import from test utilities: `from '../../__tests__/utils/render'`
3. Use mock data factories
4. Add proper accessibility tests
5. Update coverage thresholds if needed

### Test Review Guidelines
- Tests should be readable and maintainable
- Cover edge cases and error scenarios
- Include accessibility testing
- Verify responsive behavior
- Test keyboard navigation

This comprehensive testing setup ensures the MakerMatrix frontend is reliable, accessible, and maintainable across all user workflows and technical requirements.