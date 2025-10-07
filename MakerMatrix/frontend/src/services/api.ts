import type { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import axios from 'axios'
import { toast } from 'react-hot-toast'

// In development, use relative URLs to benefit from Vite proxy
// In production, use the full API URL
const isDevelopment = (import.meta as any).env?.DEV
const API_BASE_URL = isDevelopment
  ? ''
  : (import.meta as any).env?.VITE_API_URL || 'https://localhost:8443'

export interface ApiResponse<T = any> {
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
            toast.error(data?.message || 'Resource not found')
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

  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }
}

export const apiClient = new ApiClient()

// Helper function for handling API errors
export const handleApiError = (error: any): string => {
  if (error.response?.data?.message) {
    return error.response.data.message
  }
  if (error.response?.data?.error) {
    return error.response.data.error
  }
  if (error.message) {
    return error.message
  }
  return 'An unexpected error occurred'
}

// Helper function to get PDF proxy URL
export const getPDFProxyUrl = (externalUrl: string): string => {
  const isDevelopment = (import.meta as any).env?.DEV

  if (isDevelopment) {
    // Use relative URL so it goes through Vite proxy
    return `/static/proxy-pdf?url=${encodeURIComponent(externalUrl)}`
  } else {
    // Production: use full API URL
    return `${API_BASE_URL}/static/proxy-pdf?url=${encodeURIComponent(externalUrl)}`
  }
}
