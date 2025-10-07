/**
 * DigiKey-specific configuration handler
 * Handles conversion of DigiKey form fields to standard SupplierConfigCreate format
 */

import type { SupplierConfigCreate } from '../../../services/supplier.service'

export interface DigiKeyFormData {
  sandbox_mode?: boolean
  oauth_callback_url?: string
  storage_path?: string
}

/**
 * Transform DigiKey form data into standard SupplierConfigCreate format
 * Moves DigiKey-specific fields into custom_parameters
 */
export function prepareDigiKeyConfig(
  baseConfig: SupplierConfigCreate,
  digikeyData: DigiKeyFormData
): SupplierConfigCreate {
  const config = { ...baseConfig }

  // Build custom_parameters from DigiKey-specific fields
  const customParams: Record<string, any> = {}

  if (digikeyData.sandbox_mode !== undefined) {
    customParams.sandbox_mode = digikeyData.sandbox_mode
    // Update base URL based on sandbox mode
    config.base_url = digikeyData.sandbox_mode
      ? 'https://sandbox-api.digikey.com'
      : 'https://api.digikey.com'
  }

  if (digikeyData.oauth_callback_url) {
    customParams.oauth_callback_url = digikeyData.oauth_callback_url
  }

  if (digikeyData.storage_path) {
    customParams.storage_path = digikeyData.storage_path
  }

  // Merge with existing custom_parameters
  config.custom_parameters = {
    ...config.custom_parameters,
    ...customParams,
  }

  // Set DigiKey-specific defaults
  config.custom_headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...config.custom_headers,
  }

  return config
}
