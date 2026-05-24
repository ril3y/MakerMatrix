import type { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import axios from 'axios'
import { toast } from 'react-hot-toast'

// In development, use relative URLs to benefit from Vite proxy
// In production, use relative URLs (served from same origin) or explicit VITE_API_URL
interface ImportMeta {
  env?: {
    DEV?: boolean
    VITE_API_URL?: string
  }
}
const isDevelopment = (import.meta as ImportMeta).env?.DEV
const API_BASE_URL = isDevelopment ? '' : (import.meta as ImportMeta).env?.VITE_API_URL || ''

export interface ApiResponse<T = unknown> {
  status: 'success' | 'error' | 'warning'
  message: string
  data?: T
  page?: number
  page_size?: number
  total_parts?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

class ApiClient {
  private client: AxiosInstance
  private authToken: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Load token from localStorage
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      this.authToken = storedToken
    }

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiResponse>) => {
        if (error.response) {
          const { status, data } = error.response

          if (status === 401) {
            // Unauthorized - clear token and redirect to login
            this.clearAuth()
            window.location.href = '/login'
            toast.error('Session expired. Please login again.')
          } else if (status === 403) {
            toast.error('You do not have permission to perform this action.')
          } else if (status === 404) {
            // Don't show toast for enrichment requirements - these are expected for new-style suppliers
            const url = error.config?.url || ''
            if (!url.includes('/enrichment-requirements/')) {
              toast.error(data?.message || 'Resource not found')
            }
          } else if (status === 409) {
            toast.error(data?.message || 'Resource already exists')
          } else if (status === 422) {
            toast.error(data?.message || 'Validation error')
          } else if (status >= 500) {
            toast.error('Server error. Please try again later.')
          }
        } else if (error.request) {
          toast.error('Network error. Please check your connection.')
        }

        return Promise.reject(error)
      }
    )
  }

  setAuthToken(token: string) {
    this.authToken = token
    localStorage.setItem('auth_token', token)
  }

  clearAuth() {
    this.authToken = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  }

  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }
}

export const apiClient = new ApiClient()

/**
 * Extract a human-readable error message from an unknown error value. Handles:
 *  - Axios errors with `response.data.detail` (FastAPI default), `.message`,
 *    or `.error` payloads
 *  - Standard `Error` instances (uses `.message`)
 *  - Plain strings
 *  - Anything else — returns the supplied fallback
 *
 * Use this everywhere instead of casting to inline shapes like
 * `error as { response?: { data?: { detail?: string } } }`.
 */
export const getErrorMessage = (
  error: unknown,
  fallback = 'An unexpected error occurred'
): string => {
  if (error == null) return fallback
  if (typeof error === 'string') return error || fallback

  if (typeof error === 'object') {
    const axiosError = error as AxiosError<{ detail?: string; message?: string; error?: string }>
    const data = axiosError.response?.data
    if (data) {
      if (typeof data.detail === 'string' && data.detail.length > 0) return data.detail
      if (typeof data.message === 'string' && data.message.length > 0) return data.message
      if (typeof data.error === 'string' && data.error.length > 0) return data.error
    }
    const message = (axiosError as { message?: unknown }).message
    if (typeof message === 'string' && message.length > 0) return message
  }
  return fallback
}

// Backwards-compatible alias retained for callers that imported `handleApiError`.
export const handleApiError = getErrorMessage

// Helper function to get PDF proxy URL
export const getPDFProxyUrl = (externalUrl: string): string => {
  const isDevelopment = (import.meta as ImportMeta).env?.DEV

  if (isDevelopment) {
    // Use relative URL so it goes through Vite proxy
    return `/api/utility/static/proxy-pdf?url=${encodeURIComponent(externalUrl)}`
  } else {
    // Production: use full API URL
    return `${API_BASE_URL}/api/utility/static/proxy-pdf?url=${encodeURIComponent(externalUrl)}`
  }
}
