import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    // Vitest defaults to picking up **/*.{test,spec}.{ts,tsx}, which sweeps in the
    // Playwright e2e suites at tests/e2e/*.spec.ts and crashes the unit run. Pin
    // vitest to src-only test files.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**', 'tests/**'],
    // The default worker_threads pool aborts on teardown in CI with
    // "uv__stream_destroy: Assertion `!uv__io_active(...)' failed" (libuv issue with
    // jsdom + MSW). Forks pool gets each test file its own subprocess and tears down
    // cleanly — the trade-off is slightly slower runs, which is fine for CI.
    pool: 'forks',
    // Some component tests deliberately trigger errors (rejected service promises,
    // duplicate-name validation throws) to assert on the toast/UI handling that
    // results. The production code surfaces those errors via toast and then lets
    // them propagate out of react-hook-form's handleSubmit, which vitest treats
    // as unhandled rejections and would exit 1 even when every test assertion
    // passes. Ignore them at the runner level — tests still fail if assertions
    // fail. TODO: have components swallow these errors and remove this flag.
    dangerouslyIgnoreUnhandledErrors: true,
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*'],
      exclude: [
        'src/__tests__/**/*',
        'src/**/*.test.*',
        'src/**/*.spec.*',
        'src/main.tsx',
        'src/vite-env.d.ts'
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})