/**
 * LCSC-specific configuration handler
 * Handles conversion of LCSC form fields to standard SupplierConfigCreate format
 */

import type { SupplierConfigCreate } from '../../../services/supplier.service'

// LCSC doesn't have any supplier-specific fields beyond the base config
// All fields (base_url, rate_limit_per_minute, etc.) are in SupplierConfigCreate
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface LCSCFormData {}

/**
 * Transform LCSC form data into standard SupplierConfigCreate format
 * LCSC uses standard REST API with simple API key authentication, so no special transformation needed
 */
export function prepareLCSCConfig(
  baseConfig: SupplierConfigCreate,
  lcscData: LCSCFormData
): SupplierConfigCreate {
  const config = { ...baseConfig }

  // Set LCSC-specific defaults
  config.custom_headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...config.custom_headers,
  }

  return config
}
