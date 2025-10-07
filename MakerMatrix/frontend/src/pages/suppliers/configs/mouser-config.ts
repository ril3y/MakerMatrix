/**
 * Mouser-specific configuration handler
 * Handles conversion of Mouser form fields to standard SupplierConfigCreate format
 */

import { SupplierConfigCreate } from '../../../services/supplier.service'

export interface MouserFormData {
  // Mouser doesn't have any supplier-specific fields beyond the base config
  // All fields (base_url, api_version, rate_limit_per_minute, etc.) are in SupplierConfigCreate
}

/**
 * Transform Mouser form data into standard SupplierConfigCreate format
 * Mouser uses standard REST API with API key authentication, so no special transformation needed
 */
export function prepareMouserConfig(
  baseConfig: SupplierConfigCreate,
  mouserData: MouserFormData
): SupplierConfigCreate {
  const config = { ...baseConfig }

  // Set Mouser-specific defaults
  config.custom_headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...config.custom_headers,
  }

  return config
}
