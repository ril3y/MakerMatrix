import '@testing-library/jest-dom/vitest'
import { afterEach, beforeAll, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from './mocks/server'
import type { ReactNode } from 'react'
import { createElement } from 'react'

// Global framer-motion mock
vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    return ({ children, ...props }: { children?: ReactNode; [key: string]: unknown }) =>
      createElement(tag, props, children)
  }

  return {
    motion: {
      div: createMotionComponent('div'),
      button: createMotionComponent('button'),
      span: createMotionComponent('span'),
      p: createMotionComponent('p'),
      a: createMotionComponent('a'),
      form: createMotionComponent('form'),
      li: createMotionComponent('li'),
      ul: createMotionComponent('ul'),
    },
    AnimatePresence: ({ children }: { children: ReactNode }) => children,
    useAnimation: () => ({
      start: vi.fn(),
      set: vi.fn(),
    }),
    useInView: () => true,
  }
})

// Setup MSW
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  cleanup()
})
afterAll(() => server.close())

// jsdom's File/Blob don't implement `.text()` or `.arrayBuffer()`. Polyfill them
// using FileReader so utilities like `previewFile` work in tests.
if (typeof Blob !== 'undefined' && typeof Blob.prototype.text !== 'function') {
  Blob.prototype.text = function () {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => reject(reader.error)
      reader.readAsText(this)
    })
  }
}
if (typeof Blob !== 'undefined' && typeof Blob.prototype.arrayBuffer !== 'function') {
  Blob.prototype.arrayBuffer = function () {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as ArrayBuffer)
      reader.onerror = () => reject(reader.error)
      reader.readAsArrayBuffer(this)
    })
  }
}

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  readonly root: Element | null = null
  readonly rootMargin: string = ''
  readonly thresholds: ReadonlyArray<number> = []

  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
  unobserve() {}
} as unknown as typeof IntersectionObserver

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
  setItem: (key: string, value: string) => {
    localStorage[key] = value
  },
  removeItem: (key: string) => {
    delete localStorage[key]
  },
  clear: () => {
    Object.keys(localStorage).forEach((key) => delete localStorage[key])
  },
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock sessionStorage
const sessionStorageMock = {
  getItem: (key: string) => sessionStorage[key] || null,
  setItem: (key: string, value: string) => {
    sessionStorage[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorage[key]
  },
  clear: () => {
    Object.keys(sessionStorage).forEach((key) => delete sessionStorage[key])
  },
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
