/**
 * Tests for the centralized `getErrorMessage` helper. Replaces the
 * `as { response?: { data?: { detail?: string } } }` ad-hoc casts that used
 * to be scattered across the codebase.
 */
import { describe, it, expect } from 'vitest'
import type { AxiosError } from 'axios'
import { getErrorMessage, handleApiError } from '../api'

/** Build a minimal object that matches the AxiosError shape we care about. */
const axiosErr = (body: Record<string, unknown>, message = 'Request failed'): AxiosError => ({
  // We don't need the full AxiosError surface — just enough for the helper
  // to walk `response.data.{detail,message,error}` and `.message`.
  isAxiosError: true,
  message,
  name: 'AxiosError',
  config: {} as never,
  toJSON: () => ({}),
  response: {
    data: body,
    status: 400,
    statusText: 'Bad Request',
    headers: {},
    config: {} as never,
  },
})

describe('getErrorMessage', () => {
  it('prefers `response.data.detail` (FastAPI default error body)', () => {
    const err = axiosErr({ detail: 'Validation failed: bad name' })
    expect(getErrorMessage(err)).toBe('Validation failed: bad name')
  })

  it('falls back to `response.data.message` when `detail` is missing', () => {
    const err = axiosErr({ message: 'Server says no' })
    expect(getErrorMessage(err)).toBe('Server says no')
  })

  it('falls back to `response.data.error` when neither `detail` nor `message` is set', () => {
    const err = axiosErr({ error: 'legacy error key' })
    expect(getErrorMessage(err)).toBe('legacy error key')
  })

  it('falls back to the axios `.message` when no response body is present', () => {
    const err: AxiosError = {
      isAxiosError: true,
      message: 'Network Error',
      name: 'AxiosError',
      config: {} as never,
      toJSON: () => ({}),
    }
    expect(getErrorMessage(err)).toBe('Network Error')
  })

  it('returns the provided fallback for unknown error shapes', () => {
    expect(getErrorMessage(42, 'Could not load')).toBe('Could not load')
    expect(getErrorMessage(null, 'Could not load')).toBe('Could not load')
    expect(getErrorMessage(undefined, 'Could not load')).toBe('Could not load')
  })

  it('returns the default fallback when none is supplied', () => {
    expect(getErrorMessage({})).toBe('An unexpected error occurred')
  })

  it('treats a plain string error as the message', () => {
    expect(getErrorMessage('whoops')).toBe('whoops')
  })

  it('treats an empty-string detail as missing and walks to the next key', () => {
    const err = axiosErr({ detail: '', message: 'real message' })
    expect(getErrorMessage(err)).toBe('real message')
  })

  it('keeps `handleApiError` as a working alias of `getErrorMessage`', () => {
    // The alias exists so callers that previously imported `handleApiError`
    // keep working without churn.
    expect(handleApiError).toBe(getErrorMessage)
    const err = axiosErr({ detail: 'aliased' })
    expect(handleApiError(err)).toBe('aliased')
  })
})
