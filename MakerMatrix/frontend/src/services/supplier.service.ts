/**
 * Supplier Configuration Service
 *
 * API service for managing supplier configurations and enrichment profiles.
 * Credentials are now managed via environment variables.
 */

import { apiClient } from './api'

// API Response wrapper type
interface ApiResponse<T = unknown> {
  status: string
  data?: T
  message?: string
}

// Types for supplier configuration
export interface SupplierConfig {
  id: string
  supplier_name: string
  display_name: string
  description?: string
  website_url?: string
  image_url?: string
  supplier_type?: 'advanced' | 'basic' | 'simple' // Supplier type: advanced (API), basic (limited), simple (URL-only)
  api_type: 'rest' | 'graphql' | 'scraping'
  base_url: string
  api_version?: string
  rate_limit_per_minute?: number
  timeout_seconds: number
  max_retries: number
  retry_backoff: number
  enabled: boolean
  capabilities: string[]
  custom_headers: Record<string, string>
  custom_parameters: Record<string, unknown>
  created_at: string
  updated_at: string
  last_tested_at?: string
  test_status?: string
}

export interface SupplierConfigCreate {
  supplier_name: string
  display_name: string
  description?: string
  website_url?: string
  image_url?: string
  api_type?: 'rest' | 'graphql' | 'scraping'
  base_url: string
  api_version?: string
  rate_limit_per_minute?: number
  timeout_seconds?: number
  max_retries?: number
  retry_backoff?: number
  enabled?: boolean
  supports_datasheet?: boolean
  supports_image?: boolean
  supports_pricing?: boolean
  supports_stock?: boolean
  supports_specifications?: boolean
  custom_headers?: Record<string, string>
  custom_parameters?: Record<string, unknown>
  [key: string]:
    | string
    | number
    | boolean
    | Record<string, string>
    | Record<string, unknown>
    | undefined
}

export interface SupplierConfigUpdate {
  display_name?: string
  description?: string
  website_url?: string
  image_url?: string
  supplier_type?: 'advanced' | 'basic' | 'simple'
  enabled?: boolean
  // Modern capabilities array - backend driven
  capabilities?: string[]
  custom_headers?: Record<string, string>
  custom_parameters?: Record<string, unknown>
  // Legacy fields - DEPRECATED (kept for API compatibility but not used in UI)
  api_type?: 'rest' | 'graphql' | 'scraping'
  base_url?: string
  api_version?: string
  rate_limit_per_minute?: number
  timeout_seconds?: number
  max_retries?: number
  retry_backoff?: number
  supports_datasheet?: boolean
  supports_image?: boolean
  supports_pricing?: boolean
  supports_stock?: boolean
  supports_specifications?: boolean
}

export interface ConnectionTestResult {
  supplier_name: string
  success: boolean
  message: string
  test_duration_seconds: number
  tested_at: string
  error_message?: string
  details?: {
    oauth_required?: boolean
    oauth_url?: string
    environment?: string
    instructions?: string
    configuration_needed?: boolean
    missing_credentials?: string[]
    setup_url?: string
    install_command?: string
    api_reachable?: boolean
    credentials_valid?: boolean
    [key: string]: unknown
  }
}

export interface SupplierCapability {
  supplier_name: string
  capabilities: string[]
}

export interface CredentialFieldDefinition {
  field: string
  label: string
  description?: string
  type: 'text' | 'password'
  required: boolean
  placeholder?: string
  help_text?: string
  validation?: {
    min_length?: number
    max_length?: number
    pattern?: string
  }
}

/**
 * Supplier Configuration Service
 */
export class SupplierService {
  private static instance: SupplierService

  public static getInstance(): SupplierService {
    if (!SupplierService.instance) {
      SupplierService.instance = new SupplierService()
    }
    return SupplierService.instance
  }

  /**
   * Get all supplier configurations
   */
  async getSuppliers(enabledOnly: boolean = false): Promise<SupplierConfig[]> {
    const response = (await apiClient.get('/api/suppliers/config/suppliers', {
      params: { enabled_only: enabledOnly },
    })) as ApiResponse<SupplierConfig[]>
    return response.data || []
  }

  /**
   * Get specific supplier configuration
   */
  async getSupplier(supplierName: string): Promise<SupplierConfig> {
    const response = (await apiClient.get(
      `/api/suppliers/config/suppliers/${supplierName}`
    )) as ApiResponse<SupplierConfig>
    if (!response.data) {
      throw new Error(`Supplier "${supplierName}" not found`)
    }
    return response.data
  }

  /**
   * Create new supplier configuration
   */
  async createSupplier(config: SupplierConfigCreate): Promise<SupplierConfig> {
    const response = (await apiClient.post(
      '/api/suppliers/config/suppliers',
      config
    )) as ApiResponse<SupplierConfig>
    if (!response.data) {
      throw new Error('Failed to create supplier - no data returned')
    }
    return response.data
  }

  /**
   * Update supplier configuration
   */
  async updateSupplier(
    supplierName: string,
    updates: SupplierConfigUpdate
  ): Promise<SupplierConfig> {
    const response = (await apiClient.put(
      `/api/suppliers/config/suppliers/${supplierName}`,
      updates
    )) as ApiResponse<SupplierConfig>
    if (!response.data) {
      throw new Error(`Failed to update supplier "${supplierName}" - no data returned`)
    }
    return response.data
  }

  /**
   * Delete supplier configuration
   */
  async deleteSupplier(supplierName: string): Promise<void> {
    if (!supplierName || !supplierName.trim()) {
      throw new Error('Supplier name is required for deletion')
    }
    console.log(`Deleting supplier: ${supplierName}`)
    await apiClient.delete(`/api/suppliers/config/suppliers/${encodeURIComponent(supplierName)}`)
  }

  /**
   * Test supplier connection with provided credentials
   */
  async testConnection(
    supplierName: string,
    credentials: Record<string, string> = {}
  ): Promise<ConnectionTestResult> {
    const response = (await apiClient.post(`/api/suppliers/${supplierName}/test`, {
      credentials: Object.keys(credentials).length > 0 ? credentials : {},
      config: {}, // Required for supplier test endpoint
    })) as ApiResponse<ConnectionTestResult>
    console.log('Raw API response:', response.data)
    return response.data || ({} as ConnectionTestResult)
  }

  /**
   * Test existing stored credentials
   */
  async testExistingCredentials(supplierName: string): Promise<ConnectionTestResult> {
    const response = (await apiClient.get(
      `/api/suppliers/${supplierName}/credentials/test-existing`
    )) as ApiResponse<ConnectionTestResult>
    return response.data || ({} as ConnectionTestResult)
  }

  /**
   * Save credentials for a supplier
   */
  async saveCredentials(supplierName: string, credentials: Record<string, string>): Promise<void> {
    await apiClient.post(`/api/suppliers/${supplierName}/credentials`, {
      credentials,
    })
  }

  /**
   * Update credentials for a supplier (alias for saveCredentials)
   */
  async updateCredentials(
    supplierName: string,
    credentials: Record<string, string>
  ): Promise<void> {
    return this.saveCredentials(supplierName, credentials)
  }

  /**
   * Get credential status for a supplier
   */
  async getCredentialStatus(supplierName: string): Promise<{
    supplier_name: string
    is_configured: boolean
    connection_status?: {
      success: boolean
      message: string
    }
    credential_fields: Record<string, unknown>
    missing_credentials: string[]
    total_fields: number
    configured_fields: string[]
    configured_fields_count: number
  }> {
    try {
      // Add timeout to prevent infinite loading when supplier connection tests hang
      const response = await Promise.race([
        apiClient.get(`/api/suppliers/${supplierName}/credentials/status`),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Credential status check timed out')), 10000)
        ),
      ])

      // Cast response to ApiResponse type
      const apiResponse = response as unknown as ApiResponse
      // Check if response follows standard ResponseSchema format
      if (
        apiResponse.data &&
        typeof apiResponse.data === 'object' &&
        'is_configured' in apiResponse.data
      ) {
        return apiResponse.data as {
          supplier_name: string
          is_configured: boolean
          connection_status?: {
            success: boolean
            message: string
          }
          credential_fields: Record<string, unknown>
          missing_credentials: string[]
          total_fields: number
          configured_fields: string[]
          configured_fields_count: number
        }
      }
      // Fallback to direct data if not wrapped
      return apiResponse.data as {
        supplier_name: string
        is_configured: boolean
        connection_status?: {
          success: boolean
          message: string
        }
        credential_fields: Record<string, unknown>
        missing_credentials: string[]
        total_fields: number
        configured_fields: string[]
        configured_fields_count: number
      }
    } catch (error) {
      // If timeout or other error, return a default "not configured" status
      console.warn(`Credential status check failed for ${supplierName}:`, error)
      return {
        supplier_name: supplierName,
        is_configured: false,
        connection_status: {
          success: false,
          message: error instanceof Error ? error.message : 'Status check failed',
        },
        credential_fields: {},
        missing_credentials: [],
        total_fields: 0,
        configured_fields: [],
        configured_fields_count: 0,
      }
    }
  }

  /**
   * Get actual credentials for editing (unmasked values)
   */
  async getCredentials(supplierName: string): Promise<Record<string, string>> {
    const response = (await apiClient.get(
      `/api/suppliers/${supplierName}/credentials`
    )) as ApiResponse<Record<string, string>>
    return response.data || {}
  }

  /**
   * Get masked credentials for display (shows ••••• for set fields)
   */
  async getCredentialsForDisplay(supplierName: string): Promise<Record<string, string>> {
    const response = (await apiClient.get(
      `/api/suppliers/${supplierName}/credentials`
    )) as ApiResponse<Record<string, string>>
    return response.data || {}
  }

  /**
   * Get supplier capabilities
   */
  async getSupplierCapabilities(supplierName: string): Promise<string[]> {
    try {
      const response = (await apiClient.get(
        `/api/suppliers/${supplierName}/capabilities`
      )) as ApiResponse<string[]>
      return response.data || []
    } catch (error: unknown) {
      // 404 is expected for simple suppliers without API capabilities
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number } }
        if (axiosError.response?.status === 404) {
          console.log(`Supplier "${supplierName}" has no enrichment capabilities (simple supplier)`)
          return []
        }
      }
      throw error
    }
  }

  /**
   * Get credential field definitions for a supplier
   */
  async getCredentialFields(supplierName: string): Promise<CredentialFieldDefinition[]> {
    const response = (await apiClient.get(
      `/api/suppliers/config/suppliers/${supplierName}/credential-fields`
    )) as ApiResponse<CredentialFieldDefinition[]>
    return response.data || []
  }

  /**
   * Get configuration field definitions for a supplier
   */
  async getConfigFields(supplierName: string): Promise<{
    fields: CredentialFieldDefinition[]
    has_custom_fields: boolean
    supplier_name: string
  }> {
    const response = (await apiClient.get(
      `/api/suppliers/config/suppliers/${supplierName}/config-fields`
    )) as ApiResponse<{
      fields: CredentialFieldDefinition[]
      has_custom_fields: boolean
      supplier_name: string
    }>
    if (!response.data) {
      throw new Error(`Failed to get config fields for supplier "${supplierName}"`)
    }
    return response.data
  }

  /**
   * Initialize default supplier configurations
   */
  async initializeDefaults(): Promise<string[]> {
    const response = (await apiClient.post(
      '/api/suppliers/config/initialize-defaults'
    )) as ApiResponse<string[]>
    return response.data || []
  }

  /**
   * Export supplier configurations
   */
  async exportConfigurations(): Promise<SupplierConfig[]> {
    const response = (await apiClient.get('/api/suppliers/config/export')) as ApiResponse<
      SupplierConfig[]
    >
    return response.data || []
  }

  /**
   * Import supplier configurations from file
   */
  async importConfigurations(file: File): Promise<string[]> {
    const formData = new FormData()
    formData.append('file', file)

    const response = (await apiClient.post('/api/suppliers/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })) as ApiResponse<string[]>
    return response.data || []
  }

  /**
   * Get available supplier types (only suppliers with configuration files)
   */
  getAvailableSupplierTypes(): { name: string; display_name: string; description: string }[] {
    return [
      {
        name: 'lcsc',
        display_name: 'LCSC Electronics',
        description: 'Chinese electronics component supplier with EasyEDA integration',
      },
      {
        name: 'digikey',
        display_name: 'DigiKey Electronics',
        description: 'Global electronic components distributor with OAuth2 authentication',
      },
      {
        name: 'mouser',
        display_name: 'Mouser Electronics',
        description: 'Electronic component distributor with comprehensive inventory',
      },
    ]
  }

  /**
   * Get supported capabilities - DEPRECATED: Use backend API endpoints instead
   * @deprecated Use /api/suppliers/{supplier}/capabilities endpoint
   */
  getSupportedCapabilities(): { key: string; label: string; description: string }[] {
    console.warn(
      'getSupportedCapabilities is deprecated. Use backend API /api/suppliers/{supplier}/capabilities instead.'
    )
    return []
  }

  /**
   * Validate supplier configuration
   */
  validateConfig(
    config: SupplierConfigCreate | SupplierConfigUpdate,
    supplierName?: string
  ): string[] {
    const errors: string[] = []

    if ('supplier_name' in config) {
      if (!config.supplier_name?.trim()) {
        errors.push('Supplier name is required')
      } else if (!/^[a-z0-9_-]+$/.test(config.supplier_name)) {
        errors.push(
          'Supplier name must contain only lowercase letters, numbers, hyphens, and underscores'
        )
      }
    }

    if ('display_name' in config && !config.display_name?.trim()) {
      errors.push('Display name is required')
    }

    if ('base_url' in config) {
      if (!config.base_url?.trim()) {
        errors.push('Base URL is required')
      } else {
        try {
          new URL(config.base_url)
        } catch {
          errors.push('Base URL must be a valid URL')
        }
      }
    }

    if ('timeout_seconds' in config && config.timeout_seconds !== undefined) {
      if (config.timeout_seconds < 1 || config.timeout_seconds > 300) {
        errors.push('Timeout must be between 1 and 300 seconds')
      }
    }

    if ('max_retries' in config && config.max_retries !== undefined) {
      if (config.max_retries < 0 || config.max_retries > 10) {
        errors.push('Max retries must be between 0 and 10')
      }
    }

    if (
      'rate_limit_per_minute' in config &&
      config.rate_limit_per_minute !== undefined &&
      config.rate_limit_per_minute !== null
    ) {
      // LCSC-specific validation (scraping-based, more restrictive)
      if (supplierName === 'LCSC') {
        if (config.rate_limit_per_minute < 60 || config.rate_limit_per_minute > 600) {
          errors.push(
            'LCSC rate limit must be between 60-600 requests per minute (1-10 requests per second) to avoid being banned'
          )
        }
      } else {
        // General API suppliers
        if (config.rate_limit_per_minute < 1 || config.rate_limit_per_minute > 10000) {
          errors.push('Rate limit must be between 1 and 10000 requests per minute')
        }
      }
    }

    return errors
  }
}

// Export singleton instance
export const supplierService = SupplierService.getInstance()
export default supplierService
