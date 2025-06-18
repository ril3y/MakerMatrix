import '@testing-library/jest-dom/vitest'
import { afterEach, beforeAll, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from './mocks/server'

// Setup MSW
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  cleanup()
})
afterAll(() => server.close())

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock localStorage
const localStorageMock = {
  getItem: (key: string) => localStorage[key] || null,
  setItem: (key: string, value: string) => { localStorage[key] = value },
  removeItem: (key: string) => { delete localStorage[key] },
  clear: () => {
    Object.keys(localStorage).forEach(key => delete localStorage[key])
  }
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock sessionStorage
const sessionStorageMock = {
  getItem: (key: string) => sessionStorage[key] || null,
  setItem: (key: string, value: string) => { sessionStorage[key] = value },
  removeItem: (key: string) => { delete sessionStorage[key] },
  clear: () => {
    Object.keys(sessionStorage).forEach(key => delete sessionStorage[key])
  }
}
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock })

// Mock console methods in test environment
if (process.env.NODE_ENV === 'test') {
  global.console = {
    ...console,
    log: () => {},
    debug: () => {},
    info: () => {},
    warn: () => {},
    error: () => {},
  }
}