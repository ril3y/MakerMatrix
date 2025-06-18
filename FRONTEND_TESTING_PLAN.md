# MakerMatrix Frontend Testing Plan

## Overview
This document outlines a comprehensive testing strategy for the MakerMatrix frontend application to ensure all components, pages, and user workflows are thoroughly tested.

## Testing Stack

### Core Testing Tools
- **Vitest**: Fast unit testing framework (modern alternative to Jest)
- **Testing Library**: Component testing with React Testing Library
- **Playwright**: End-to-end testing for full application workflows
- **MSW (Mock Service Worker)**: API mocking for isolated testing
- **@testing-library/jest-dom**: Extended matchers for DOM assertions

### Additional Testing Tools
- **@testing-library/user-event**: User interaction simulation
- **axe-core**: Accessibility testing
- **@storybook/react**: Component documentation and visual testing
- **Chromatic**: Visual regression testing (optional)

## Testing Categories

### 1. Unit Tests
**Coverage**: Individual components, utilities, hooks, services
**Framework**: Vitest + React Testing Library

#### Components to Test:
- **UI Components** (`src/components/ui/`)
  - Modal.tsx
  - FormField.tsx  
  - LoadingScreen.tsx
  - ThemeSelector.tsx
  - Tooltip.tsx

- **Business Components** (`src/components/`)
  - Parts components (AddPartModal, PartEnrichmentModal)
  - Location components (AddLocationModal, EditLocationModal)
  - Category components (AddCategoryModal, EditCategoryModal)
  - Import components (FileUpload, ImportProgress, etc.)
  - Printer components (PrinterModal)
  - Supplier components (SupplierConfigPage, DynamicAddSupplierModal)

#### Services to Test:
- **API Services** (`src/services/`)
  - parts.service.ts
  - categories.service.ts
  - locations.service.ts
  - supplier.service.ts
  - auth.service.ts
  - tasks.service.ts

#### Hooks to Test:
- useAuth.ts
- useDarkMode.ts
- useOrderImport.ts

#### Utilities to Test:
- Custom utility functions
- Theme management
- Data transformations

### 2. Integration Tests
**Coverage**: Component interactions, form submissions, state management
**Framework**: Vitest + React Testing Library + MSW

#### Key Integration Flows:
- **Authentication Flow**: Login → Dashboard → Logout
- **Part Management**: Create → Edit → Delete → Search
- **Import Workflow**: Upload CSV → Preview → Import → Validate
- **Supplier Configuration**: Add → Configure → Test → Delete
- **Category Management**: Create → Assign to Parts → Delete
- **Location Management**: Create hierarchy → Assign parts → Navigate

### 3. End-to-End Tests
**Coverage**: Complete user workflows across entire application
**Framework**: Playwright

#### Critical User Journeys:
1. **New User Onboarding**
   - Login → First part creation → Location setup → Category setup

2. **Daily Inventory Management**
   - Search parts → Update quantities → Print labels → Export data

3. **Bulk Import Workflow**
   - Upload CSV → Preview → Configure → Import → Verify results

4. **Supplier Integration**
   - Configure supplier → Test connection → Enrich parts → Monitor tasks

5. **Administrative Tasks**
   - User management → Settings configuration → Analytics review

### 4. Visual Regression Tests
**Coverage**: UI consistency across different states and themes
**Framework**: Playwright + Visual comparisons

#### Visual Test Scenarios:
- Light/Dark theme variations
- Different screen sizes (mobile, tablet, desktop)
- Loading states and empty states
- Error states and validation messages
- Modal overlays and complex layouts

### 5. Accessibility Tests
**Coverage**: WCAG 2.1 AA compliance
**Framework**: axe-core + Testing Library

#### Accessibility Checks:
- Keyboard navigation
- Screen reader compatibility
- Color contrast ratios
- Focus management
- ARIA labels and semantics

## Test Implementation

### Phase 1: Setup Testing Infrastructure
```bash
# Install testing dependencies
npm install --save-dev \
  vitest \
  @vitejs/plugin-react \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jsdom \
  msw \
  @playwright/test \
  axe-core \
  @axe-core/playwright

# Install type definitions
npm install --save-dev \
  @types/testing-library__jest-dom
```

### Phase 2: Core Component Tests
- Start with UI components (Modal, FormField, etc.)
- Add service layer tests with MSW mocking
- Test critical business components

### Phase 3: Integration Testing
- Form submission flows
- API integration with mocked responses
- State management interactions

### Phase 4: E2E Testing Setup
- Playwright configuration
- Database seeding for consistent test data
- User journey automation

### Phase 5: Advanced Testing
- Visual regression testing
- Performance testing
- Accessibility auditing

## Testing Organization

### Directory Structure
```
MakerMatrix/frontend/
├── src/
│   ├── __tests__/           # Test utilities and setup
│   │   ├── setup.ts
│   │   ├── mocks/
│   │   │   ├── api.ts
│   │   │   ├── data.ts
│   │   │   └── handlers.ts
│   │   └── utils/
│   │       ├── render.tsx
│   │       └── test-utils.ts
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Modal.test.tsx
│   │   │   ├── FormField.test.tsx
│   │   │   └── ...
│   │   └── parts/
│   │       ├── AddPartModal.test.tsx
│   │       └── ...
│   ├── services/
│   │   ├── parts.service.test.ts
│   │   └── ...
│   └── hooks/
│       ├── useAuth.test.ts
│       └── ...
├── tests/
│   ├── e2e/
│   │   ├── auth.spec.ts
│   │   ├── parts.spec.ts
│   │   ├── suppliers.spec.ts
│   │   └── ...
│   └── visual/
│       ├── components.spec.ts
│       └── pages.spec.ts
└── playwright.config.ts
```

## Test Configuration Files

### Vitest Configuration
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*'],
      exclude: ['src/__tests__/**/*', 'src/**/*.test.*']
    }
  }
})
```

### Playwright Configuration
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    }
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI
  }
})
```

## Test Data Management

### Mock Data Strategy
- Use MSW for API mocking
- Create realistic test data factories
- Maintain data consistency across tests
- Use database seeding for E2E tests

### Test Database
- Use `dev_manager.py` to start backend server for E2E tests
- Create test data fixtures
- Implement database cleanup between tests

## Coverage Goals

### Code Coverage Targets
- **Unit Tests**: 90%+ coverage for utilities, hooks, services
- **Component Tests**: 85%+ coverage for all components
- **Integration Tests**: Cover all critical user workflows
- **E2E Tests**: Cover all main application features

### Testing Metrics
- All critical paths tested
- All error scenarios covered
- Performance benchmarks established
- Accessibility compliance verified

## Implementation Priority

### High Priority (Phase 1)
1. Authentication and authorization flows
2. Part management (CRUD operations)
3. Supplier configuration
4. Import/export functionality

### Medium Priority (Phase 2)
1. Advanced search and filtering
2. Task management and monitoring
3. Settings and configuration
4. Analytics and reporting

### Low Priority (Phase 3)
1. Visual regression tests
2. Performance testing
3. Advanced accessibility testing
4. Mobile-specific flows

## Integration with Dev Manager

### Backend Server Management
Use the existing `dev_manager.py` for consistent test environments:

```python
# Test helper to start backend for E2E tests
def start_test_server():
    manager = EnhancedServerManager()
    manager.start_backend()
    return manager

def stop_test_server(manager):
    manager.stop_backend()
```

### Test Environment Setup
- Use separate test database
- Mock external API calls
- Ensure consistent test data
- Handle authentication tokens

## Continuous Integration

### GitHub Actions Pipeline
```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run test:unit
      - run: npm run test:integration
      - run: npx playwright install
      - run: npm run test:e2e
      - run: npm run test:accessibility
```

### Quality Gates
- All tests must pass
- Coverage thresholds met
- No accessibility violations
- Visual regression checks pass

## Maintenance Strategy

### Test Maintenance
- Regular test review and updates
- Remove flaky tests
- Update test data as features evolve
- Performance monitoring of test suite

### Documentation
- Keep test documentation updated
- Document testing patterns and best practices
- Maintain test data documentation
- Update coverage reports regularly

This comprehensive testing plan ensures that the MakerMatrix frontend is thoroughly tested at all levels, providing confidence in the application's reliability and user experience.