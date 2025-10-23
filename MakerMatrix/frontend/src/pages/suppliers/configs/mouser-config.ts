/**
 * Mouser-specific configuration handler
 * Handles conversion of Mouser form fields to standard SupplierConfigCreate format
 */

import type { SupplierConfigCreate } from '../../../services/supplier.service'

// Mouser doesn't have any supplier-specific fields beyond the base config
// All fields (base_url, api_version, rate_limit_per_minute, etc.) are in SupplierConfigCreate
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface MouserFormData {}

/**
 * Transform Mouser form data into standard SupplierConfigCreate format
 * Mouser uses standard REST API with API key authentication, so no special transformation needed
 */
export function prepareMouserConfig(
  baseConfig: SupplierConfigCreate,
  _mouserData: MouserFormData
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
