// Printer Configuration
export interface PrinterConfig {
  backend: string
  driver?: string
  printer_identifier: string
  dpi: number
  model: string
  scaling_factor: number
  additional_settings?: Record<string, any>
}

// AI Configuration
export interface AIConfig {
  enabled: boolean
  provider: string
  api_url: string
  api_key?: string
  model_name: string
  temperature: number
  max_tokens: number
  system_prompt: string
  additional_settings?: Record<string, any>
}

export interface AIConfigUpdate {
  enabled?: boolean
  provider?: string
  api_url?: string
  api_key?: string
  model_name?: string
  temperature?: number
  max_tokens?: number
  system_prompt?: string
  additional_settings?: Record<string, any>
}

// Backup Status
export interface BackupStatus {
  database_size: number
  last_modified: string
  total_records: number
  parts_count: number
  locations_count: number
  categories_count: number
}