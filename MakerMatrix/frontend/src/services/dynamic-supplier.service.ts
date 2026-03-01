/**
 * Dynamic Supplier Service
 *
 * Interfaces with the new modular supplier system to dynamically discover suppliers,
 * get their configuration schemas, and interact with them.
 */

import { apiClient, type ApiResponse } from './api'

// Types for dynamic supplier system
export type FieldValue = string | number | boolean | null

export interface FieldDefinition {
  name: string
  label: string
  field_type: string
  required: boolean
  description?: string
  placeholder?: string
  help_text?: string
  default_value?: FieldValue
  options?: Array<{ value: string; label: string }>
  validation?: {
    min_length?: number
    max_length?: number
    pattern?: string
  }
}

export interface SupplierInfo {
  name: string
  display_name: string
  description: string
  website_url?: string
  api_documentation_url?: string
  supports_oauth: boolean
  rate_limit_info?: string
  capabilities: string[]
}

export type SpecificationValue = string | number | boolean | null | string[]

export interface PartSearchResult {
  supplier_part_number: string
  part_name?: string // Product name (e.g., "Adafruit Feather M4 CAN Express")
  manufacturer?: string
  manufacturer_part_number?: string
  description?: string
  category?: string
  datasheet_url?: string
  image_url?: string
  stock_quantity?: number
  pricing?: Array<{ quantity: number; price: number; currency: string }>
  specifications?: Record<string, SpecificationValue>
  additional_data?: Record<string, unknown>
}

export type CredentialValue = string | number | boolean | null

export interface SupplierCredentialsConfig {
  credentials: Record<string, CredentialValue>
  config?: Record<string, CredentialValue>
}

export interface TestConnectionResult {
  success: boolean
  message: string
  details?: Record<string, unknown>
}

export interface EnrichmentFieldMapping {
  field_name: string
  display_name: string
  url_patterns: string[]
  example: string
  description?: string
  required_for_enrichment: boolean
}

/**
 * Dynamic Supplier Service
 */
export class DynamicSupplierService {
  private static instance: DynamicSupplierService

  public static getInstance(): DynamicSupplierService {
    if (!DynamicSupplierService.instance) {
      DynamicSupplierService.instance = new DynamicSupplierService()
    }
    return DynamicSupplierService.instance
  }

  /**
   * Get all available suppliers
   */
  async getAvailableSuppliers(): Promise<string[]> {
    try {
      const response = await apiClient.get<ApiResponse<string[]>>('/api/suppliers/')
      return response.data || []
    } catch (error) {
      console.error('Failed to fetch available suppliers:', error)
      return []
    }
  }

  /**
   * Get list of configured and enabled suppliers (for dropdowns)
   */
  async getConfiguredSuppliers(): Promise<
    Array<{ id: string; name: string; description: string; configured: boolean; enabled: boolean }>
  > {
    try {
      type ConfiguredSupplier = {
        id: string
        name: string
        description: string
        configured: boolean
        enabled: boolean
      }
      const response = await apiClient.get<ApiResponse<ConfiguredSupplier[]>>(
        '/api/suppliers/configured'
      )
      return response.data || []
    } catch (error) {
      console.error('Failed to fetch configured suppliers:', error)
      return []
    }
  }

  /**
   * Get information about all suppliers
   */
  async getAllSuppliersInfo(): Promise<Record<string, SupplierInfo>> {
    try {
      const response =
        await apiClient.get<ApiResponse<Record<string, SupplierInfo>>>('/api/suppliers/info')
      return response.data || {}
    } catch (error) {
      console.error('Failed to fetch suppliers info:', error)
      throw new Error(
        `Failed to load suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    }
  }

  /**
   * Get information about a specific supplier
   */
  async getSupplierInfo(supplierName: string): Promise<SupplierInfo> {
    try {
      const response = await apiClient.get<ApiResponse<SupplierInfo>>(
        `/api/suppliers/${supplierName}/info`
      )

      if (response.data) {
        return response.data
      }

      throw new Error('Invalid response structure')
    } catch (error) {
      console.error(`Failed to get supplier info for ${supplierName}:`, error)
      throw error
    }
  }

  /**
   * Get credential schema for a supplier
   */
  async getCredentialSchema(supplierName: string): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.get<ApiResponse<FieldDefinition[]>>(
        `/api/suppliers/${supplierName}/credentials-schema`
      )

      if (response.data) {
        return Array.isArray(response.data) ? response.data : []
      }

      return []
    } catch (error) {
      console.error(`Failed to get credential schema for ${supplierName}:`, error)
      return []
    }
  }

  /**
   * Get configuration schema for a supplier
   */
  async getConfigurationSchema(supplierName: string): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.get<ApiResponse<FieldDefinition[]>>(
        `/api/suppliers/${supplierName}/config-schema`
      )

      if (response.data) {
        return Array.isArray(response.data) ? response.data : []
      }

      return []
    } catch (error) {
      console.error(`Failed to get configuration schema for ${supplierName}:`, error)
      return []
    }
  }

  /**
   * Get credential schema for a supplier with current configuration context
   */
  async getCredentialSchemaWithConfig(
    supplierName: string,
    credentials: Record<string, CredentialValue>,
    config: Record<string, CredentialValue>
  ): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.post<ApiResponse<FieldDefinition[]>>(
        `/api/suppliers/${supplierName}/credentials-schema-with-config`,
        {
          credentials,
          config,
        }
      )

      if (response.data) {
        return Array.isArray(response.data) ? response.data : []
      }

      return []
    } catch (error) {
      console.error(`Failed to get credential schema with config for ${supplierName}:`, error)
      return []
    }
  }

  /**
   * Get configuration schema for a supplier with current configuration context
   */
  async getConfigurationSchemaWithConfig(
    supplierName: string,
    credentials: Record<string, CredentialValue>,
    config: Record<string, CredentialValue>
  ): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.post<ApiResponse<FieldDefinition[]>>(
        `/api/suppliers/${supplierName}/config-schema-with-config`,
        {
          credentials,
          config,
        }
      )

      if (response.data) {
        return Array.isArray(response.data) ? response.data : []
      }

      return []
    } catch (error) {
      console.error(`Failed to get configuration schema with config for ${supplierName}:`, error)
      return []
    }
  }

  /**
   * Get capabilities for a supplier
   */
  async getSupplierCapabilities(supplierName: string): Promise<string[]> {
    const response = await apiClient.get<ApiResponse<string[]>>(
      `/api/suppliers/${supplierName}/capabilities`
    )
    return response.data || []
  }

  /**
   * Get enrichment field mappings (URL patterns) for a supplier
   */
  async getEnrichmentFieldMappings(supplierName: string): Promise<EnrichmentFieldMapping[]> {
    try {
      const response = await apiClient.get<ApiResponse<EnrichmentFieldMapping[]>>(
        `/api/suppliers/${supplierName}/enrichment-field-mappings`
      )

      if (response.data) {
        return Array.isArray(response.data) ? response.data : []
      }

      return []
    } catch (error) {
      console.error(`Failed to get enrichment field mappings for ${supplierName}:`, error)
      return []
    }
  }

  /**
   * Get environment variable defaults for supplier credentials
   */
  async getSupplierEnvDefaults(supplierName: string): Promise<Record<string, CredentialValue>> {
    try {
      const response = await apiClient.get<ApiResponse<Record<string, CredentialValue>>>(
        `/api/suppliers/${supplierName}/env-defaults`
      )

      if (response.data) {
        return response.data
      }

      return {}
    } catch (error) {
      console.error(`Failed to get environment defaults for ${supplierName}:`, error)
      return {}
    }
  }

  /**
   * Test connection to supplier
   */
  async testConnection(
    supplierName: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<TestConnectionResult> {
    try {
      const response = await apiClient.post<ApiResponse<TestConnectionResult>>(
        `/api/suppliers/${supplierName}/test`,
        {
          credentials,
          config: config || {},
        }
      )

      if (response.data) {
        return response.data
      }

      // Fallback response
      return {
        success: false,
        message: 'Invalid response from server',
      }
    } catch (error) {
      console.error(`Test connection failed for ${supplierName}:`, error)
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
      }
    }
  }

  /**
   * Get OAuth authorization URL (for suppliers that support OAuth)
   */
  async getOAuthAuthorizationUrl(
    supplierName: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<string> {
    const response = await apiClient.post<ApiResponse<string>>(
      `/api/suppliers/${supplierName}/oauth/authorization-url`,
      {
        credentials,
        config: config || {},
      }
    )
    return response.data as string
  }

  /**
   * Exchange OAuth authorization code for tokens
   */
  async exchangeOAuthCode(
    supplierName: string,
    authorizationCode: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<{ authenticated: boolean }> {
    const response = await apiClient.post<ApiResponse<{ authenticated: boolean }>>(
      `/api/suppliers/${supplierName}/oauth/exchange`,
      {
        authorization_code: authorizationCode,
        credentials,
        config: config || {},
      }
    )
    return response.data as { authenticated: boolean }
  }

  /**
   * Get detailed information about a specific part
   */
  async getPartDetails(
    supplierName: string,
    partNumber: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<PartSearchResult> {
    const response = await apiClient.post<ApiResponse<PartSearchResult>>(
      `/api/suppliers/${supplierName}/part/${partNumber}`,
      {
        credentials,
        config: config || {},
      }
    )

    if (response.data) {
      return response.data
    }

    throw new Error('Invalid response format from getPartDetails')
  }

  /**
   * Get datasheet URL for a part
   */
  async getPartDatasheet(
    supplierName: string,
    partNumber: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<string> {
    const response = await apiClient.post<ApiResponse<string>>(
      `/api/suppliers/${supplierName}/part/${partNumber}/datasheet`,
      {
        credentials,
        config: config || {},
      }
    )
    return response.data as string
  }

  /**
   * Get pricing for a part
   */
  async getPartPricing(
    supplierName: string,
    partNumber: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<Array<{ quantity: number; price: number; currency: string }>> {
    const response = await apiClient.post<
      ApiResponse<Array<{ quantity: number; price: number; currency: string }>>
    >(`/api/suppliers/${supplierName}/part/${partNumber}/pricing`, {
      credentials,
      config: config || {},
    })
    return response.data || []
  }

  /**
   * Get stock level for a part
   */
  async getPartStock(
    supplierName: string,
    partNumber: string,
    credentials: Record<string, CredentialValue>,
    config?: Record<string, CredentialValue>
  ): Promise<number> {
    const response = await apiClient.post<ApiResponse<number>>(
      `/api/suppliers/${supplierName}/part/${partNumber}/stock`,
      {
        credentials,
        config: config || {},
      }
    )
    return response.data ?? 0
  }

  /**
   * Check if a supplier supports web scraping fallback
   */
  async checkScrapingSupport(supplierName: string): Promise<{
    supports_scraping: boolean
    requires_js: boolean
    warning: string | null
    rate_limit_seconds: number | null
  }> {
    try {
      const response = await apiClient.get<
        ApiResponse<{
          supports_scraping: boolean
          requires_js: boolean
          warning: string | null
          rate_limit_seconds: number | null
        }>
      >(`/api/suppliers/${supplierName}/supports-scraping`)

      if (response.data) {
        return response.data
      }

      return {
        supports_scraping: false,
        requires_js: false,
        warning: null,
        rate_limit_seconds: null,
      }
    } catch (error) {
      console.error(`Failed to check scraping support for ${supplierName}:`, error)
      return {
        supports_scraping: false,
        requires_js: false,
        warning: null,
        rate_limit_seconds: null,
      }
    }
  }

  /**
   * Detect supplier from URL by checking against known supplier patterns
   */
  async detectSupplierFromUrl(url: string): Promise<{
    supplier_name: string
    display_name: string
    confidence: number
  } | null> {
    try {
      const response = await apiClient.post<
        ApiResponse<{
          supplier_name: string
          display_name: string
          confidence: number
        } | null>
      >(`/api/suppliers/detect-from-url`, { url })

      if (response.data) {
        return response.data
      }

      return null
    } catch (error) {
      console.error('Failed to detect supplier from URL:', error)
      return null
    }
  }

  /**
   * Upload a file for a supplier configuration
   */
  async uploadSupplierFile(supplierName: string, file: File): Promise<string> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      // axios automatically sets multipart/form-data when passing FormData
      const response = await apiClient.post<
        ApiResponse<{
          file_path: string
          filename: string
        }>
      >(`/api/suppliers/${supplierName}/file-upload`, formData)

      if (response.data && response.data.file_path) {
        return response.data.file_path
      }

      throw new Error('Invalid response from file upload')
    } catch (error) {
      console.error(`Failed to upload file for ${supplierName}:`, error)
      throw error
    }
  }
}

// Export singleton instance
export const dynamicSupplierService = DynamicSupplierService.getInstance()
export default dynamicSupplierService
