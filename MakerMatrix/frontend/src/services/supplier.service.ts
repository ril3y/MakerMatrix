/**
 * Supplier Configuration Service
 * 
 * API service for managing supplier configurations, credentials, and enrichment profiles.
 * Handles encrypted credential storage and supplier capability management.
 */

import { apiClient } from './api';

// Types for supplier configuration
export interface SupplierConfig {
  id: string;
  supplier_name: string;
  display_name: string;
  description?: string;
  api_type: 'rest' | 'graphql' | 'scraping';
  base_url: string;
  api_version?: string;
  rate_limit_per_minute?: number;
  timeout_seconds: number;
  max_retries: number;
  retry_backoff: number;
  enabled: boolean;
  capabilities: string[];
  custom_headers: Record<string, string>;
  custom_parameters: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_tested_at?: string;
  test_status?: string;
  has_credentials: boolean;
}

export interface SupplierConfigCreate {
  supplier_name: string;
  display_name: string;
  description?: string;
  api_type?: 'rest' | 'graphql' | 'scraping';
  base_url: string;
  api_version?: string;
  rate_limit_per_minute?: number;
  timeout_seconds?: number;
  max_retries?: number;
  retry_backoff?: number;
  enabled?: boolean;
  supports_datasheet?: boolean;
  supports_image?: boolean;
  supports_pricing?: boolean;
  supports_stock?: boolean;
  supports_specifications?: boolean;
  custom_headers?: Record<string, string>;
  custom_parameters?: Record<string, any>;
}

export interface SupplierConfigUpdate {
  display_name?: string;
  description?: string;
  api_type?: 'rest' | 'graphql' | 'scraping';
  base_url?: string;
  api_version?: string;
  rate_limit_per_minute?: number;
  timeout_seconds?: number;
  max_retries?: number;
  retry_backoff?: number;
  enabled?: boolean;
  supports_datasheet?: boolean;
  supports_image?: boolean;
  supports_pricing?: boolean;
  supports_stock?: boolean;
  supports_specifications?: boolean;
  custom_headers?: Record<string, string>;
  custom_parameters?: Record<string, any>;
}

export interface SupplierCredentials {
  api_key?: string;
  secret_key?: string;
  username?: string;
  password?: string;
  oauth_token?: string;
  refresh_token?: string;
  additional_data?: Record<string, string>;
}

export interface ConnectionTestResult {
  supplier_name: string;
  success: boolean;
  test_duration_seconds: number;
  tested_at: string;
  error_message?: string;
}

export interface SupplierCapability {
  supplier_name: string;
  capabilities: string[];
}

export interface CredentialFieldDefinition {
  field: string;
  label: string;
  description?: string;
  type: 'text' | 'password';
  required: boolean;
  placeholder?: string;
  help_text?: string;
  validation?: {
    min_length?: number;
    max_length?: number;
    pattern?: string;
  };
}

/**
 * Supplier Configuration Service
 */
export class SupplierService {
  private static instance: SupplierService;
  
  public static getInstance(): SupplierService {
    if (!SupplierService.instance) {
      SupplierService.instance = new SupplierService();
    }
    return SupplierService.instance;
  }

  /**
   * Get all supplier configurations
   */
  async getSuppliers(enabledOnly: boolean = false): Promise<SupplierConfig[]> {
    const response = await apiClient.get('/api/config/suppliers', {
      params: { enabled_only: enabledOnly }
    });
    return response.data.data || response.data || [];
  }

  /**
   * Get specific supplier configuration
   */
  async getSupplier(supplierName: string, includeCredentials: boolean = false): Promise<SupplierConfig> {
    const response = await apiClient.get(`/api/config/suppliers/${supplierName}`, {
      params: { include_credentials: includeCredentials }
    });
    return response.data.data;
  }

  /**
   * Create new supplier configuration
   */
  async createSupplier(config: SupplierConfigCreate): Promise<SupplierConfig> {
    const response = await apiClient.post('/api/config/suppliers', config);
    return response.data.data;
  }

  /**
   * Update supplier configuration
   */
  async updateSupplier(supplierName: string, updates: SupplierConfigUpdate): Promise<SupplierConfig> {
    const response = await apiClient.put(`/api/config/suppliers/${supplierName}`, updates);
    return response.data.data;
  }

  /**
   * Delete supplier configuration
   */
  async deleteSupplier(supplierName: string): Promise<void> {
    if (!supplierName || !supplierName.trim()) {
      throw new Error('Supplier name is required for deletion');
    }
    console.log(`Deleting supplier: ${supplierName}`);
    await apiClient.delete(`/api/config/suppliers/${encodeURIComponent(supplierName)}`);
  }

  /**
   * Test supplier connection
   */
  async testConnection(supplierName: string): Promise<ConnectionTestResult> {
    const response = await apiClient.post(`/api/config/suppliers/${supplierName}/test`);
    console.log('Raw API response:', response.data);
    return response.data.data || response.data;
  }

  /**
   * Get supplier capabilities
   */
  async getSupplierCapabilities(supplierName: string): Promise<string[]> {
    const response = await apiClient.get(`/api/config/suppliers/${supplierName}/capabilities`);
    return response.data.data;
  }

  /**
   * Get credential field definitions for a supplier
   */
  async getCredentialFields(supplierName: string): Promise<CredentialFieldDefinition[]> {
    const response = await apiClient.get(`/api/config/suppliers/${supplierName}/credential-fields`);
    return response.data.data;
  }

  /**
   * Get configuration field definitions for a supplier
   */
  async getConfigFields(supplierName: string): Promise<{
    fields: CredentialFieldDefinition[];
    has_custom_fields: boolean;
    supplier_name: string;
  }> {
    const response = await apiClient.get(`/api/config/suppliers/${supplierName}/config-fields`);
    return response.data.data;
  }

  /**
   * Store supplier credentials
   */
  async storeCredentials(supplierName: string, credentials: SupplierCredentials): Promise<void> {
    await apiClient.post('/api/config/credentials', {
      supplier_name: supplierName,
      ...credentials
    });
  }

  /**
   * Update supplier credentials
   */
  async updateCredentials(supplierName: string, credentials: SupplierCredentials): Promise<void> {
    await apiClient.put(`/api/config/credentials/${supplierName}`, credentials);
  }

  /**
   * Delete supplier credentials
   */
  async deleteCredentials(supplierName: string): Promise<void> {
    await apiClient.delete(`/api/config/credentials/${supplierName}`);
  }

  /**
   * Initialize default supplier configurations
   */
  async initializeDefaults(): Promise<string[]> {
    const response = await apiClient.post('/api/config/initialize-defaults');
    return response.data.data;
  }

  /**
   * Export supplier configurations
   */
  async exportConfigurations(includeCredentials: boolean = false): Promise<any> {
    const response = await apiClient.get('/api/config/export', {
      params: { include_credentials: includeCredentials }
    });
    return response.data.data;
  }

  /**
   * Import supplier configurations from file
   */
  async importConfigurations(file: File): Promise<string[]> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/api/config/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.data;
  }

  /**
   * Get available supplier types (only suppliers with configuration files)
   */
  getAvailableSupplierTypes(): { name: string; display_name: string; description: string }[] {
    return [
      {
        name: 'lcsc',
        display_name: 'LCSC Electronics',
        description: 'Chinese electronics component supplier with EasyEDA integration'
      },
      {
        name: 'digikey',
        display_name: 'DigiKey Electronics',
        description: 'Global electronic components distributor with OAuth2 authentication'
      },
      {
        name: 'mouser',
        display_name: 'Mouser Electronics', 
        description: 'Electronic component distributor with comprehensive inventory'
      }
    ];
  }

  /**
   * Get supported capabilities
   */
  getSupportedCapabilities(): { key: string; label: string; description: string }[] {
    return [
      {
        key: 'fetch_datasheet',
        label: 'Datasheet Download',
        description: 'Download component datasheets'
      },
      {
        key: 'fetch_image',
        label: 'Image Download', 
        description: 'Download component images'
      },
      {
        key: 'fetch_pricing',
        label: 'Pricing Information',
        description: 'Retrieve current pricing data'
      },
      {
        key: 'fetch_stock',
        label: 'Stock Information',
        description: 'Check availability and stock levels'
      },
      {
        key: 'fetch_specifications',
        label: 'Technical Specifications',
        description: 'Retrieve detailed component specifications'
      }
    ];
  }

  /**
   * Validate supplier configuration
   */
  validateConfig(config: SupplierConfigCreate | SupplierConfigUpdate, supplierName?: string): string[] {
    const errors: string[] = [];

    if ('supplier_name' in config) {
      if (!config.supplier_name?.trim()) {
        errors.push('Supplier name is required');
      } else if (!/^[a-z0-9_-]+$/.test(config.supplier_name)) {
        errors.push('Supplier name must contain only lowercase letters, numbers, hyphens, and underscores');
      }
    }

    if ('display_name' in config && !config.display_name?.trim()) {
      errors.push('Display name is required');
    }

    if ('base_url' in config) {
      if (!config.base_url?.trim()) {
        errors.push('Base URL is required');
      } else {
        try {
          new URL(config.base_url);
        } catch {
          errors.push('Base URL must be a valid URL');
        }
      }
    }

    if ('timeout_seconds' in config && config.timeout_seconds !== undefined) {
      if (config.timeout_seconds < 1 || config.timeout_seconds > 300) {
        errors.push('Timeout must be between 1 and 300 seconds');
      }
    }

    if ('max_retries' in config && config.max_retries !== undefined) {
      if (config.max_retries < 0 || config.max_retries > 10) {
        errors.push('Max retries must be between 0 and 10');
      }
    }

    if ('rate_limit_per_minute' in config && config.rate_limit_per_minute !== undefined && config.rate_limit_per_minute !== null) {
      // LCSC-specific validation (scraping-based, more restrictive)
      if (supplierName === 'LCSC') {
        if (config.rate_limit_per_minute < 60 || config.rate_limit_per_minute > 600) {
          errors.push('LCSC rate limit must be between 60-600 requests per minute (1-10 requests per second) to avoid being banned');
        }
      } else {
        // General API suppliers
        if (config.rate_limit_per_minute < 1 || config.rate_limit_per_minute > 10000) {
          errors.push('Rate limit must be between 1 and 10000 requests per minute');
        }
      }
    }

    return errors;
  }
}

// Export singleton instance
export const supplierService = SupplierService.getInstance();
export default supplierService;