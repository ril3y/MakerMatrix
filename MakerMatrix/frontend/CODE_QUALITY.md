# Code Quality Guide

This document outlines the code quality tools, practices, and standards for the MakerMatrix frontend.

## Table of Contents

- [Overview](#overview)
- [Linting](#linting)
- [Code Formatting](#code-formatting)
- [TypeScript](#typescript)
- [Testing](#testing)
- [Pre-commit Hooks](#pre-commit-hooks)
- [NPM Scripts](#npm-scripts)
- [Best Practices](#best-practices)

## Overview

The MakerMatrix frontend uses a comprehensive suite of tools to ensure code quality:

- **ESLint** - TypeScript and React linting
- **Prettier** - Code formatting
- **TypeScript** - Type checking
- **Vitest** - Unit and integration testing
- **Playwright** - End-to-end testing
- **lint-staged** - Pre-commit checks (optional with Husky)

## Linting

### ESLint Configuration

ESLint is configured in `.eslintrc.json` with the following features:

- TypeScript support with `@typescript-eslint` plugin
- React Hooks rules enforcement
- Prettier integration to avoid conflicts
- Unused imports cleanup
- Consistent type imports

### Running the Linter

```bash
# Check for linting errors
npm run lint

# Auto-fix linting errors
npm run lint:fix
```

### Key Rules

- **TypeScript unused variables**: Warns about unused vars (allows `_` prefix)
- **No explicit any**: Warns when using `any` type
- **React Hooks**: Errors on hooks violations
- **Unused imports**: Automatically removes unused imports
- **Console statements**: Warns on `console.log` (allows `console.warn/error/info`)

## Code Formatting

### Prettier Configuration

Prettier is configured in `.prettierrc`:

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

### Running Prettier

```bash
# Format all files
npm run format

# Check formatting without modifying files
npm run format:check
```

### Editor Integration

**VS Code** - Install the Prettier extension and enable format on save:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

## TypeScript

### Type Checking

Run type checking without emitting files:

```bash
npm run type-check
```

### TypeScript Configuration

The project uses modern TypeScript with the following key settings:

- **Target**: ES2020
- **Module**: ESNext
- **Strict mode**: Disabled (gradual migration recommended)
- **Path mapping**: `@/*` maps to `src/*`

### Type Imports

Prefer type-only imports when importing types:

```typescript
// ✅ Good
import type { User } from '@/types/user'
import { getUser } from '@/services/user'

// ❌ Avoid
import { User, getUser } from '@/services/user'
```

## Testing

### Unit and Integration Tests (Vitest)

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests once and exit
npm run test:run

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

### End-to-End Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run E2E tests in headed mode (see browser)
npm run test:e2e:headed

# Run visual regression tests
npm run test:visual
```

### Writing Tests

Follow the established patterns in existing test files:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

describe('ComponentName', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render correctly', () => {
    render(<ComponentName />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })

  it('should handle user interaction', async () => {
    const user = userEvent.setup()
    render(<ComponentName />)

    await user.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(screen.getByText('Result')).toBeInTheDocument()
    })
  })
})
```

### Test Coverage

Aim for:
- **Statements**: > 80%
- **Branches**: > 75%
- **Functions**: > 80%
- **Lines**: > 80%

## Pre-commit Hooks

### lint-staged Configuration

The `.lintstagedrc.json` file defines what runs on staged files:

```json
{
  "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
  "*.{json,md,css}": ["prettier --write"]
}
```

### Setting Up Hooks (Optional)

To enable automatic pre-commit checks:

1. Ensure git repository is initialized
2. Run: `npx husky init` (if not already set up)
3. Create `.husky/pre-commit` with:

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

cd MakerMatrix/frontend && npx lint-staged
```

## NPM Scripts

### Code Quality Scripts

```bash
# Run all quality checks
npm run quality

# Auto-fix all quality issues
npm run quality:fix
```

The `quality` script runs:
1. Format checking with Prettier
2. Linting with ESLint
3. Type checking with TypeScript

### Development Scripts

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Best Practices

### Code Organization

1. **Components** - Keep components focused and single-purpose
2. **Hooks** - Extract reusable logic into custom hooks
3. **Services** - Centralize API calls in service files
4. **Types** - Define types in `types/` directory

### Naming Conventions

- **Components**: PascalCase (`UserProfile.tsx`)
- **Hooks**: camelCase with `use` prefix (`useAuth.ts`)
- **Services**: camelCase with `.service` suffix (`parts.service.ts`)
- **Types**: PascalCase (`User`, `PartCreate`)
- **Constants**: UPPER_SNAKE_CASE (`API_BASE_URL`)

### Import Organization

Organize imports in this order:

1. External libraries (React, etc.)
2. Internal absolute imports (`@/components`)
3. Relative imports (`./Component`)
4. Type imports
5. CSS imports

```typescript
// External
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

// Internal
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'

// Relative
import { Header } from './Header'

// Types
import type { User } from '@/types/user'

// Styles
import './styles.css'
```

### Component Structure

```typescript
// 1. Imports
import { useState } from 'react'
import type { Props } from './types'

// 2. Types/Interfaces
interface ComponentProps {
  title: string
  onSubmit: () => void
}

// 3. Component
const Component = ({ title, onSubmit }: ComponentProps) => {
  // 4. Hooks
  const [state, setState] = useState('')

  // 5. Handlers
  const handleClick = () => {
    // ...
  }

  // 6. Effects
  useEffect(() => {
    // ...
  }, [])

  // 7. Render
  return <div>{title}</div>
}

// 8. Export
export default Component
```

### Error Handling

```typescript
// ✅ Good - Specific error handling
try {
  await api.call()
} catch (error: unknown) {
  const message = error instanceof Error
    ? error.message
    : 'An error occurred'
  toast.error(message)
}

// ❌ Avoid - Swallowing errors
try {
  await api.call()
} catch (error) {
  // Silent failure
}
```

### Async/Await

```typescript
// ✅ Good - Error handling with loading states
const [loading, setLoading] = useState(false)

const handleSubmit = async () => {
  try {
    setLoading(true)
    await api.submit(data)
    toast.success('Success!')
  } catch (error) {
    toast.error('Failed to submit')
  } finally {
    setLoading(false)
  }
}

// ❌ Avoid - No error handling or loading states
const handleSubmit = async () => {
  await api.submit(data)
  toast.success('Success!')
}
```

### State Management

```typescript
// ✅ Good - Single source of truth
const [formData, setFormData] = useState({
  name: '',
  email: '',
})

const updateField = (field: string, value: string) => {
  setFormData(prev => ({ ...prev, [field]: value }))
}

// ❌ Avoid - Multiple related states
const [name, setName] = useState('')
const [email, setEmail] = useState('')
```

## Continuous Integration

The project includes GitHub Actions workflows for:

- Running tests on PRs
- Type checking
- Linting
- Building production bundle
- E2E testing across browsers

See `.github/workflows/` for CI configuration.

## Resources

- [ESLint Rules](https://eslint.org/docs/rules/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Documentation](https://playwright.dev/)
- [Vitest Documentation](https://vitest.dev/)

## Getting Help

For questions or issues:

1. Check existing test files for examples
2. Review this documentation
3. Consult team members
4. Open an issue with detailed description

---

**Last Updated**: January 2025
