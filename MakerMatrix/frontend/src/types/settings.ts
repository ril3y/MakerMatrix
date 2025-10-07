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

// CSV Import Configuration
export interface CSVImportConfig {
  download_datasheets: boolean
  download_images: boolean
  overwrite_existing_files: boolean
  max_concurrent_downloads: number
  download_timeout_seconds: number
  create_backup_before_import: boolean
  show_progress: boolean
}

export interface CSVImportConfigUpdate {
  download_datasheets?: boolean
  download_images?: boolean
  overwrite_existing_files?: boolean
  max_concurrent_downloads?: number
  download_timeout_seconds?: number
  create_backup_before_import?: boolean
  show_progress?: boolean
}

// Import Progress
export interface ImportProgress {
  total_parts: number
  processed_parts: number
  successful_parts: number
  failed_parts: number
  current_operation: string
  is_downloading: boolean
  download_progress?: {
    current_file: string
    files_downloaded: number
    total_files: number
  }
  errors: string[]
  start_time: string
  estimated_completion?: string
}
