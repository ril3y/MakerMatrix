/**
 * Dynamic Supplier Service
 * 
 * Interfaces with the new modular supplier system to dynamically discover suppliers,
 * get their configuration schemas, and interact with them.
 */

import { apiClient } from './api';

// Types for dynamic supplier system
export interface FieldDefinition {
  name: string;
  label: string;
  field_type: string;
  required: boolean;
  description?: string;
  placeholder?: string;
  help_text?: string;
  default_value?: any;
  options?: Array<{value: string; label: string}>;
  validation?: {
    min_length?: number;
    max_length?: number;
    pattern?: string;
  };
}

export interface SupplierInfo {
  name: string;
  display_name: string;
  description: string;
  website_url?: string;
  api_documentation_url?: string;
  supports_oauth: boolean;
  rate_limit_info?: string;
  capabilities: string[];
}

export interface PartSearchResult {
  supplier_part_number: string;
  manufacturer?: string;
  manufacturer_part_number?: string;
  description?: string;
  category?: string;
  datasheet_url?: string;
  image_url?: string;
  stock_quantity?: number;
  pricing?: Array<{quantity: number; price: number; currency: string}>;
  specifications?: Record<string, any>;
  additional_data?: Record<string, any>;
}

export interface SupplierCredentialsConfig {
  credentials: Record<string, any>;
  config?: Record<string, any>;
}

export interface TestConnectionResult {
  success: boolean;
  message: string;
  details?: Record<string, any>;
}

/**
 * Dynamic Supplier Service
 */
export class DynamicSupplierService {
  private static instance: DynamicSupplierService;
  
  public static getInstance(): DynamicSupplierService {
    if (!DynamicSupplierService.instance) {
      DynamicSupplierService.instance = new DynamicSupplierService();
    }
    return DynamicSupplierService.instance;
  }

  /**
   * Get all available suppliers
   */
  async getAvailableSuppliers(): Promise<string[]> {
    const response = await apiClient.get('/api/suppliers/');
    return response.data.data;
  }

  /**
   * Get information about all suppliers
   */
  async getAllSuppliersInfo(): Promise<Record<string, SupplierInfo>> {
    try {
      const response = await apiClient.get('/api/suppliers/info');
      
      // The apiClient.get() method returns response.data directly
      // Check if it has the standard ResponseSchema structure
      if (response && typeof response === 'object' && response.data) {
        return response.data;
      }
      
      // Fallback: check if the response itself is the data
      if (response && response.digikey && response.lcsc && response.mouser) {
        return response;
      }
      
      return {};
    } catch (error) {
      console.error('Failed to fetch suppliers info:', error);
      throw new Error(`Failed to load suppliers: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get information about a specific supplier
   */
  async getSupplierInfo(supplierName: string): Promise<SupplierInfo> {
    try {
      const response = await apiClient.get(`/api/suppliers/${supplierName}/info`);
      console.log(`getSupplierInfo(${supplierName}) response:`, response);
      
      if (response && response.data) {
        return response.data;
      }
      
      throw new Error('Invalid response structure');
    } catch (error) {
      console.error(`Failed to get supplier info for ${supplierName}:`, error);
      throw error;
    }
  }

  /**
   * Get credential schema for a supplier
   */
  async getCredentialSchema(supplierName: string): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.get(`/api/suppliers/${supplierName}/credentials-schema`);
      console.log(`getCredentialSchema(${supplierName}) response:`, response);
      
      if (response && response.data) {
        return Array.isArray(response.data) ? response.data : [];
      }
      
      return [];
    } catch (error) {
      console.error(`Failed to get credential schema for ${supplierName}:`, error);
      return [];
    }
  }

  /**
   * Get configuration schema for a supplier
   */
  async getConfigurationSchema(supplierName: string): Promise<FieldDefinition[]> {
    try {
      const response = await apiClient.get(`/api/suppliers/${supplierName}/config-schema`);
      console.log(`getConfigurationSchema(${supplierName}) response:`, response);
      
      if (response && response.data) {
        return Array.isArray(response.data) ? response.data : [];
      }
      
      return [];
    } catch (error) {
      console.error(`Failed to get configuration schema for ${supplierName}:`, error);
      return [];
    }
  }

  /**
   * Get capabilities for a supplier
   */
  async getSupplierCapabilities(supplierName: string): Promise<string[]> {
    const response = await apiClient.get(`/api/suppliers/${supplierName}/capabilities`);
    return response.data.data;
  }

  /**
   * Get environment variable defaults for supplier credentials
   */
  async getSupplierEnvDefaults(supplierName: string): Promise<Record<string, any>> {
    try {
      const response = await apiClient.get(`/api/suppliers/${supplierName}/env-defaults`);
      console.log(`getSupplierEnvDefaults(${supplierName}) response:`, response);
      
      if (response && response.data) {
        return response.data;
      }
      
      return {};
    } catch (error) {
      console.error(`Failed to get environment defaults for ${supplierName}:`, error);
      return {};
    }
  }

  /**
   * Test connection to supplier
   */
  async testConnection(supplierName: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<TestConnectionResult> {
    try {
      console.log(`Testing connection for ${supplierName} with:`, { credentials, config });
      const response = await apiClient.post(`/api/suppliers/${supplierName}/test`, {
        credentials,
        config: config || {}
      });
      console.log(`Test connection response for ${supplierName}:`, response);
      
      if (response && response.data) {
        return response.data;
      }
      
      // Fallback response
      return {
        success: false,
        message: 'Invalid response from server'
      };
    } catch (error) {
      console.error(`Test connection failed for ${supplierName}:`, error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed'
      };
    }
  }

  /**
   * Get OAuth authorization URL (for suppliers that support OAuth)
   */
  async getOAuthAuthorizationUrl(supplierName: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<string> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/oauth/authorization-url`, {
      credentials,
      config: config || {}
    });
    return response.data.data;
  }

  /**
   * Exchange OAuth authorization code for tokens
   */
  async exchangeOAuthCode(supplierName: string, authorizationCode: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<{authenticated: boolean}> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/oauth/exchange`, {
      authorization_code: authorizationCode,
      credentials,
      config: config || {}
    });
    return response.data.data;
  }

  /**
   * Search for parts using a supplier
   */
  async searchParts(supplierName: string, query: string, credentials: Record<string, any>, config?: Record<string, any>, limit: number = 50): Promise<PartSearchResult[]> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/search`, {
      query,
      limit,
      config_request: {
        credentials,
        config: config || {}
      }
    });
    return response.data.data;
  }

  /**
   * Get detailed information about a specific part
   */
  async getPartDetails(supplierName: string, partNumber: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<PartSearchResult> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/part/${partNumber}`, {
      credentials,
      config: config || {}
    });
    return response.data.data;
  }

  /**
   * Get datasheet URL for a part
   */
  async getPartDatasheet(supplierName: string, partNumber: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<string> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/part/${partNumber}/datasheet`, {
      credentials,
      config: config || {}
    });
    return response.data.data;
  }

  /**
   * Get pricing for a part
   */
  async getPartPricing(supplierName: string, partNumber: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<Array<{quantity: number; price: number; currency: string}>> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/part/${partNumber}/pricing`, {
      credentials,
      config: config || {}
    });
    return response.data.data;
  }

  /**
   * Get stock level for a part
   */
  async getPartStock(supplierName: string, partNumber: string, credentials: Record<string, any>, config?: Record<string, any>): Promise<number> {
    const response = await apiClient.post(`/api/suppliers/${supplierName}/part/${partNumber}/stock`, {
      credentials,
      config: config || {}
    });
    return response.data.data;
  }
}

// Export singleton instance
export const dynamicSupplierService = DynamicSupplierService.getInstance();
export default dynamicSupplierService;