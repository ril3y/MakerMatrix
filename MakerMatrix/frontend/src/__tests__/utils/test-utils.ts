import type { UserEvent } from '@testing-library/user-event'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

/**
 * Setup user event for testing user interactions
 */
export const setupUser = (): UserEvent => {
  return userEvent.setup()
}

/**
 * Create test data factories for consistent test data
 */
export const createMockPart = (overrides = {}) => ({
  id: 'test-part-1',
  part_name: 'Test Resistor',
  part_number: 'R001',
  description: 'Test resistor 10K ohm',
  quantity: 100,
  supplier: 'LCSC',
  location_id: 'test-location-1',
  image_url: null,
  additional_properties: {},
  categories: [],
  order_items: [],
  order_summary: null,
  datasheets: [],
  ...overrides,
})

export const createMockLocation = (overrides = {}) => ({
  id: 'test-location-1',
  name: 'Test Storage',
  description: 'Test storage location',
  parent_id: null,
  location_type: 'standard',
  parent: null,
  children: [],
  parts: [],
  ...overrides,
})

export const createMockCategory = (overrides = {}) => ({
  id: 'test-category-1',
  name: 'Resistors',
  description: 'Electronic resistors',
  parts: [],
  ...overrides,
})

export const createMockUser = (overrides = {}) => ({
  id: 'test-user-1',
  username: 'testuser',
  email: 'test@example.com',
  is_active: true,
  password_change_required: false,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-01-01T00:00:00Z',
  roles: ['user'],
  ...overrides,
})

export const createMockSupplier = (overrides = {}) => ({
  id: 'test-supplier-1',
  supplier_name: 'TESTSUPPLIER',
  display_name: 'Test Supplier',
  description: 'Test supplier for testing',
  api_type: 'rest',
  base_url: 'https://api.testsupplier.com',
  api_version: 'v1',
  rate_limit_per_minute: 100,
  timeout_seconds: 30,
  max_retries: 3,
  retry_backoff: 1.0,
  enabled: true,
  capabilities: ['fetch_pricing', 'fetch_datasheet'],
  custom_headers: {},
  custom_parameters: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  last_tested_at: null,
  test_status: null,
  ...overrides,
})

export const createMockTask = (overrides = {}) => ({
  id: 'test-task-1',
  task_type: 'PART_ENRICHMENT',
  name: 'Test Task',
  description: 'Test task description',
  status: 'PENDING',
  priority: 'NORMAL',
  progress_percentage: 0,
  current_step: 'Starting',
  input_data: '{}',
  result_data: '{}',
  error_message: null,
  max_retries: 3,
  retry_count: 0,
  timeout_seconds: 300,
  created_at: '2024-01-01T00:00:00Z',
  started_at: null,
  completed_at: null,
  created_by_user_id: 'test-user-1',
  ...overrides,
})

/**
 * Utility to wait for async operations
 */
export const waitFor = (ms: number): Promise<void> => {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Mock file for file upload testing
 */
export const createMockFile = (
  name = 'test.csv',
  content = 'header1,header2\nvalue1,value2',
  type = 'text/csv'
): File => {
  return new File([content], name, { type })
}

/**
 * Mock drag and drop events
 */
export const createMockDragEvent = (files: File[]) => ({
  dataTransfer: {
    files,
    items: files.map((file) => ({
      kind: 'file',
      getAsFile: () => file,
    })),
    types: ['Files'],
  },
  preventDefault: () => {},
  stopPropagation: () => {},
})

/**
 * Assert element has expected accessibility attributes
 */
export const expectAccessibleElement = (element: HTMLElement) => {
  expect(element).toBeVisible()

  // Check for proper labeling
  if (
    element.tagName === 'INPUT' ||
    element.tagName === 'TEXTAREA' ||
    element.tagName === 'SELECT'
  ) {
    expect(element).toHaveAccessibleName()
  }

  // Check for proper roles
  if (element.getAttribute('role')) {
    expect(element).toHaveAttribute('role')
  }
}

/**
 * Mock console methods for testing
 */
export const mockConsole = () => {
  const originalConsole = { ...console }
  const mockMethods = {
    log: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  }

  Object.assign(console, mockMethods)

  return {
    restore: () => Object.assign(console, originalConsole),
    ...mockMethods,
  }
}
