/**
 * Dynamic Supplier Service
 *
 * Interfaces with the new modular supplier system to dynamically discover suppliers,
 * get their configuration schemas, and interact with them.
 */

import { apiClient } from './api'

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
      const response = (await apiClient.get('/api/suppliers/')) as {
        data?: string[] | { data: string[] }
      }
      console.log('getAvailableSuppliers raw response:', response)
      console.log('getAvailableSuppliers response.data:', response.data)

      // Handle different response formats
      const data = response.data as { data: string[] } | string[] | undefined
      if (data && typeof data === 'object' && 'data' in data && Array.isArray(data.data)) {
        return data.data
      } else if (data && Array.isArray(data)) {
        return data
      } else if (response && Array.isArray(response)) {
        return response as string[]
      }

      console.warn('Unexpected response format for available suppliers:', response)
      return []
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
      const response = (await apiClient.get('/api/suppliers/configured')) as {
        data?: ConfiguredSupplier[] | { data: ConfiguredSupplier[] }
      }

      // Handle different response formats
      const data = response.data as
        | { data: ConfiguredSupplier[] }
        | ConfiguredSupplier[]
        | undefined
      if (data && Array.isArray(data)) {
        return data
      } else if (data && typeof data === 'object' && 'data' in data && Array.isArray(data.data)) {
        return data.data
      } else {
        console.warn('Unexpected response format for configured suppliers:', response)
        return []
      }
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
      const response = (await apiClient.get('/api/suppliers/info')) as
        | { data: Record<string, SupplierInfo> }
        | Record<string, SupplierInfo>

      // The apiClient.get() method returns response.data directly
      // Check if it has the standard ResponseSchema structure
      if (response && typeof response === 'object' && 'data' in response) {
        const data = response.data
        if (data && typeof data === 'object' && !('name' in data)) {
          return data as Record<string, SupplierInfo>
        }
      }

      // Fallback: check if the response itself is the data (Record<string, SupplierInfo>)
      if (response && typeof response === 'object' && !('data' in response)) {
        return response as Record<string, SupplierInfo>
      }

      return {}
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
      const response = (await apiClient.get(`/api/suppliers/${supplierName}/info`)) as {
        data: SupplierInfo
      }
      console.log(`getSupplierInfo(${supplierName}) response:`, response)

      if (response && response.data) {
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
      const response = (await apiClient.get(
        `/api/suppliers/${supplierName}/credentials-schema`
      )) as {
        data: FieldDefinition[]
      }
      console.log(`getCredentialSchema(${supplierName}) response:`, response)

      if (response && response.data) {
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
      const response = (await apiClient.get(`/api/suppliers/${supplierName}/config-schema`)) as {
        data: FieldDefinition[]
      }
      console.log(`getConfigurationSchema(${supplierName}) response:`, response)

      if (response && response.data) {
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
      const response = (await apiClient.post(
        `/api/suppliers/${supplierName}/credentials-schema-with-config`,
        {
          credentials,
          config,
        }
      )) as {
        data: FieldDefinition[]
      }
      console.log(`getCredentialSchemaWithConfig(${supplierName}) response:`, response)

      if (response && response.data) {
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
      const response = (await apiClient.post(
        `/api/suppliers/${supplierName}/config-schema-with-config`,
        {
          credentials,
          config,
        }
      )) as {
        data: FieldDefinition[]
      }
      console.log(`getConfigurationSchemaWithConfig(${supplierName}) response:`, response)

      if (response && response.data) {
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
    const response = (await apiClient.get(`/api/suppliers/${supplierName}/capabilities`)) as {
      data: { data: string[] }
    }
    return response.data.data
  }

  /**
   * Get enrichment field mappings (URL patterns) for a supplier
   */
  async getEnrichmentFieldMappings(supplierName: string): Promise<EnrichmentFieldMapping[]> {
    try {
      const response = (await apiClient.get(
        `/api/suppliers/${supplierName}/enrichment-field-mappings`
      )) as {
        data: EnrichmentFieldMapping[]
      }

      if (response && response.data) {
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
      const response = (await apiClient.get(`/api/suppliers/${supplierName}/env-defaults`)) as {
        data: Record<string, CredentialValue>
      }
      console.log(`getSupplierEnvDefaults(${supplierName}) response:`, response)

      if (response && response.data) {
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
      console.log(`Testing connection for ${supplierName} with:`, { credentials, config })
      const response = (await apiClient.post(`/api/suppliers/${supplierName}/test`, {
        credentials,
        config: config || {},
      })) as {
        data: TestConnectionResult
      }
      console.log(`Test connection response for ${supplierName}:`, response)

      if (response && response.data) {
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
    const response = (await apiClient.post(
      `/api/suppliers/${supplierName}/oauth/authorization-url`,
      {
        credentials,
        config: config || {},
      }
    )) as {
      data: { data: string }
    }
    return response.data.data
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
    const response = (await apiClient.post(`/api/suppliers/${supplierName}/oauth/exchange`, {
      authorization_code: authorizationCode,
      credentials,
      config: config || {},
    })) as {
      data: { data: { authenticated: boolean } }
    }
    return response.data.data
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
    const response = (await apiClient.post(`/api/suppliers/${supplierName}/part/${partNumber}`, {
      credentials,
      config: config || {},
    })) as { data: { data: PartSearchResult } } | { data: PartSearchResult } | PartSearchResult

    // Handle different response formats (apiClient.post may return different structures)
    if (response && typeof response === 'object' && 'data' in response) {
      const dataWrapper = response.data as { data: PartSearchResult } | PartSearchResult
      if (dataWrapper && typeof dataWrapper === 'object' && 'data' in dataWrapper) {
        return dataWrapper.data
      } else if (
        dataWrapper &&
        typeof dataWrapper === 'object' &&
        'supplier_part_number' in dataWrapper
      ) {
        return dataWrapper as PartSearchResult
      }
    } else if (response && typeof response === 'object' && 'supplier_part_number' in response) {
      return response as PartSearchResult
    }

    console.error('Unexpected response format from getPartDetails:', response)
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
    const response = (await apiClient.post(
      `/api/suppliers/${supplierName}/part/${partNumber}/datasheet`,
      {
        credentials,
        config: config || {},
      }
    )) as {
      data: { data: string }
    }
    return response.data.data
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
    const response = (await apiClient.post(
      `/api/suppliers/${supplierName}/part/${partNumber}/pricing`,
      {
        credentials,
        config: config || {},
      }
    )) as {
      data: { data: Array<{ quantity: number; price: number; currency: string }> }
    }
    return response.data.data
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
    const response = (await apiClient.post(
      `/api/suppliers/${supplierName}/part/${partNumber}/stock`,
      {
        credentials,
        config: config || {},
      }
    )) as {
      data: { data: number }
    }
    return response.data.data
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
      const response = (await apiClient.get(
        `/api/suppliers/${supplierName}/supports-scraping`
      )) as {
        data: {
          supports_scraping: boolean
          requires_js: boolean
          warning: string | null
          rate_limit_seconds: number | null
        }
      }

      if (response && response.data) {
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
      const response = (await apiClient.post(`/api/suppliers/detect-from-url`, { url })) as {
        data: {
          supplier_name: string
          display_name: string
          confidence: number
        } | null
      }

      if (response && response.data) {
        return response.data
      }

      return null
    } catch (error) {
      console.error('Failed to detect supplier from URL:', error)
      return null
    }
  }
}

// Export singleton instance
export const dynamicSupplierService = DynamicSupplierService.getInstance()
export default dynamicSupplierService
