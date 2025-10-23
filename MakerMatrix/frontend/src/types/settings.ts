// Printer Configuration
export interface PrinterConfig {
  backend: string
  driver?: string
  printer_identifier: string
  dpi: number
  model: string
  scaling_factor: number
  additional_settings?: Record<string, unknown>
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
  additional_settings?: Record<string, unknown>
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
  additional_settings?: Record<string, unknown>
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

// Printer Types
export interface Printer {
  printer_id: string
  name: string
  driver_type: string
  model: string
  backend: string
  identifier: string
  dpi: number
  scaling_factor: number
  status?: string
}

export interface PrinterInfo {
  printer_id: string
  name: string
  driver_type: string
  model: string
  backend: string
  identifier: string
  dpi: number
  scaling_factor: number
  capabilities?: Record<string, unknown>
}

export interface PrinterStatus {
  printer_id: string
  status: string
  is_ready?: boolean
  error?: string
}

export interface PrinterTestResult {
  success: boolean
  message: string
  details?: Record<string, unknown>
}

export interface PrintTestLabelRequest {
  printer_id: string
  text: string
  label_size: string
  copies: number
}

export interface PrintAdvancedLabelRequest {
  printer_id: string
  template: string
  text: string
  label_size: string
  label_length?: number
  options: {
    fit_to_label: boolean
    include_qr: boolean
    qr_data?: string
  }
  data?: Record<string, unknown>
}

export interface PreviewAdvancedLabelRequest {
  template: string
  text: string
  label_size: string
  label_length?: number
  options: {
    fit_to_label: boolean
    include_qr: boolean
    qr_data?: string
  }
  data?: Record<string, unknown>
}

export interface PreviewResponse {
  success: boolean
  preview_data?: string
  format?: string
  error?: string
  message?: string
}

export interface RegisterPrinterRequest {
  printer_id: string
  name: string
  driver_type: string
  model: string
  backend: string
  identifier: string
  dpi: number
  scaling_factor: number
}

export interface UpdatePrinterRequest {
  name: string
  driver_type: string
  model: string
  backend: string
  identifier: string
  dpi: number
  scaling_factor: number
}

export interface PrinterDriver {
  driver_type: string
  name: string
  description?: string
  supported_models?: string[]
  capabilities?: Record<string, unknown>
}

export interface DriverInfo {
  driver_type: string
  name: string
  description?: string
  supported_backends?: string[]
  default_dpi?: number
  capabilities?: Record<string, unknown>
}

export interface PrinterSetupTest {
  printer: Printer
}

export interface DiscoveryStatus {
  task_id: string
  status: string
  progress?: number
  discovered_printers?: Printer[]
  error?: string
}

export interface LatestDiscovery {
  task_id: string
  status: string
  discovered_printers?: Printer[]
  completed_at?: string
}

export interface AIModel {
  id: string
  name: string
  provider?: string
  size?: string
  description?: string
}

export interface AvailableModelsResponse {
  models: AIModel[]
  provider: string
  current_model?: string
}

// Import.meta environment types
export interface ImportMetaEnv {
  VITE_API_URL?: string
  [key: string]: string | undefined
}

export interface ImportMeta {
  env: ImportMetaEnv
}
