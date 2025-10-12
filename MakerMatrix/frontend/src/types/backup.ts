/**
 * Backup System Types
 */

export interface BackupConfig {
  id: string
  schedule_enabled: boolean
  schedule_type: 'nightly' | 'weekly' | 'custom'
  schedule_cron: string | null
  retention_count: number
  last_backup_at: string | null
  next_backup_at: string | null
  encryption_required: boolean
  encryption_password: string | null
  created_at: string
  updated_at: string
}

export interface BackupInfo {
  filename: string
  encrypted: boolean
  size_bytes: number
  size_mb: number
  created_at: string
  download_url: string
}

export interface BackupListResponse {
  backups: BackupInfo[]
  total_count: number
  total_size_mb: number
}

export interface BackupStatus {
  database: {
    size_mb: number
    last_modified: string
    path: string
  }
  backups: {
    count: number
    total_size_mb: number
    latest_backup: {
      filename: string
      size_mb: number
      created_at: string
      encrypted: boolean
    } | null
  }
  configuration: {
    schedule_enabled: boolean
    schedule_type: string
    retention_count: number
    last_backup_at: string | null
    next_backup_at: string | null
  } | null
}

export interface CreateBackupRequest {
  password?: string
  include_datasheets?: boolean
  include_images?: boolean
  include_env?: boolean
}

export interface RestoreBackupRequest {
  backup_file: File
  password?: string
  create_safety_backup?: boolean
}

export interface BackupTaskResponse {
  task_id: string
  task_type: string
  task_name: string
  status: string
  priority: string
  backup_name?: string
  encrypted?: boolean
  safety_backup_enabled?: boolean
  monitor_url: string
  expected_backup_location?: string
  warning?: string
}
