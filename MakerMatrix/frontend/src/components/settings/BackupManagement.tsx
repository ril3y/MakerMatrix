/**
 * Backup Management Component
 *
 * Comprehensive backup, restore, and scheduling UI for MakerMatrix
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Database,
  Download,
  Upload,
  RefreshCw,
  Calendar,
  Trash2,
  Lock,
  Shield,
  Clock,
  AlertTriangle,
  CheckCircle,
  Settings as SettingsIcon,
  Save,
  Play,
  HardDrive,
  Eye,
  EyeOff
} from 'lucide-react'
import toast from 'react-hot-toast'
import { backupService } from '@/services/backup.service'
import type {
  BackupConfig,
  BackupInfo,
  BackupStatus as BackupStatusType
} from '@/types/backup'

const BackupManagement = () => {
  const [backupConfig, setBackupConfig] = useState<BackupConfig | null>(null)
  const [backupStatus, setBackupStatus] = useState<BackupStatusType | null>(null)
  const [backupList, setBackupList] = useState<BackupInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'backup' | 'restore' | 'schedule'>('backup')

  // Task progress tracking
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState<number>(0)
  const [taskStatus, setTaskStatus] = useState<string>('')

  // Backup creation state
  const [backupPassword, setBackupPassword] = useState('')
  const [showBackupPassword, setShowBackupPassword] = useState(false)
  const [includeDatasheets, setIncludeDatasheets] = useState(true)
  const [includeImages, setIncludeImages] = useState(true)
  const [includeEnv, setIncludeEnv] = useState(true)

  // Restore state
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [restorePassword, setRestorePassword] = useState('')
  const [showRestorePassword, setShowRestorePassword] = useState(false)
  const [createSafetyBackup, setCreateSafetyBackup] = useState(true)

  // Schedule password state
  const [showSchedulePassword, setShowSchedulePassword] = useState(false)
  const [schedulePassword, setSchedulePassword] = useState('')
  const [passwordIsSet, setPasswordIsSet] = useState(false)

  useEffect(() => {
    loadBackupData()
  }, [])

  // Monitor active task progress
  useEffect(() => {
    if (!activeTaskId) return

    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch(`/api/tasks/${activeTaskId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          const data = await response.json()
          const task = data.data

          setTaskProgress(task.progress_percentage || 0)
          setTaskStatus(task.current_step || task.status)

          // If task is completed or failed, stop monitoring
          if (task.status === 'completed' || task.status === 'failed') {
            setActiveTaskId(null)
            setTaskProgress(0)
            setTaskStatus('')

            if (task.status === 'completed') {
              toast.success('Backup completed successfully!')
            } else {
              toast.error('Backup task failed')
            }

            // Reload backup list
            setTimeout(loadBackupData, 1000)
          }
        }
      } catch (error) {
        console.error('Failed to fetch task progress:', error)
      }
    }, 1000) // Poll every second

    return () => clearInterval(interval)
  }, [activeTaskId])

  const loadBackupData = async () => {
    setLoading(true)
    try {
      const [config, status, list, passwordSet] = await Promise.all([
        backupService.getBackupConfig(),
        backupService.getBackupStatus(),
        backupService.listBackups(),
        backupService.isPasswordSet()
      ])

      setBackupConfig(config)
      setBackupStatus(status)
      setBackupList(list)
      setPasswordIsSet(passwordSet)

      // Clear the password field when loading
      setSchedulePassword('')
    } catch (error) {
      toast.error('Failed to load backup data')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateBackup = async () => {
    try {
      const task = await backupService.createBackup({
        password: backupPassword || undefined,
        include_datasheets: includeDatasheets,
        include_images: includeImages,
        include_env: includeEnv
      })

      toast.success('Backup task created - monitoring progress...')

      // Clear password after creating backup
      setBackupPassword('')

      // Start monitoring task progress
      setActiveTaskId(task.task_id)
      setTaskProgress(0)
      setTaskStatus('Starting backup...')
    } catch (error) {
      toast.error('Failed to create backup')
    }
  }

  const handleRestoreBackup = async () => {
    if (!restoreFile) {
      toast.error('Please select a backup file')
      return
    }

    try {
      const task = await backupService.restoreBackup({
        backup_file: restoreFile,
        password: restorePassword || undefined,
        create_safety_backup: createSafetyBackup
      })

      toast.success('Restore task created successfully')
      toast('Application will restart after restore completes', { icon: '⚠️' })

      // Clear state
      setRestoreFile(null)
      setRestorePassword('')
    } catch (error) {
      toast.error('Failed to create restore task')
    }
  }

  const handleDeleteBackup = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete backup: ${filename}?`)) {
      return
    }

    try {
      await backupService.deleteBackup(filename)
      toast.success('Backup deleted successfully')
      loadBackupData()
    } catch (error) {
      toast.error('Failed to delete backup')
    }
  }

  const handleDownloadBackup = async (filename: string) => {
    try {
      await backupService.downloadBackup(filename)
      toast.success('Backup download started')
    } catch (error) {
      toast.error('Failed to download backup')
    }
  }

  const handleUpdateConfig = async () => {
    if (!backupConfig) return

    try {
      // Include the password if user entered one (empty string clears it)
      const configToSave = {
        ...backupConfig,
        encryption_password: schedulePassword || undefined
      }

      await backupService.updateBackupConfig(configToSave)
      toast.success('Backup configuration updated successfully')
      loadBackupData()
    } catch (error) {
      toast.error('Failed to update configuration')
    }
  }

  const handleRunRetention = async () => {
    try {
      const task = await backupService.runRetentionCleanup()
      toast.success('Retention cleanup task created')
      setTimeout(loadBackupData, 3000)
    } catch (error) {
      toast.error('Failed to start retention cleanup')
    }
  }

  if (loading && !backupConfig) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
        <p className="text-secondary mt-2">Loading backup settings...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
          <Database className="w-5 h-5" />
          Backup Management
        </h3>
        <button
          onClick={loadBackupData}
          className="btn btn-secondary flex items-center gap-2"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Status Cards */}
      {backupStatus && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Database Size</p>
                <p className="text-2xl font-bold text-primary">
                  {backupStatus.database.size_mb.toFixed(2)} MB
                </p>
              </div>
              <HardDrive className="w-8 h-8 text-primary opacity-20" />
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Total Backups</p>
                <p className="text-2xl font-bold text-primary">
                  {backupStatus.backups.count}
                </p>
                <p className="text-xs text-secondary mt-1">
                  {backupStatus.backups.total_size_mb.toFixed(2)} MB total
                </p>
              </div>
              <Database className="w-8 h-8 text-primary opacity-20" />
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-secondary">Latest Backup</p>
                {backupStatus.backups.latest_backup ? (
                  <>
                    <p className="text-lg font-bold text-primary">
                      {new Date(backupStatus.backups.latest_backup.created_at).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-secondary mt-1">
                      {backupStatus.backups.latest_backup.size_mb.toFixed(2)} MB
                      {backupStatus.backups.latest_backup.encrypted && ' 🔒'}
                    </p>
                  </>
                ) : (
                  <p className="text-lg text-secondary">None</p>
                )}
              </div>
              <Clock className="w-8 h-8 text-primary opacity-20" />
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('backup')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'backup'
              ? 'border-b-2 border-primary text-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Download className="w-4 h-4 inline mr-2" />
          Create Backup
        </button>
        <button
          onClick={() => setActiveTab('restore')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'restore'
              ? 'border-b-2 border-primary text-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Upload className="w-4 h-4 inline mr-2" />
          Restore
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'schedule'
              ? 'border-b-2 border-primary text-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          <Calendar className="w-4 h-4 inline mr-2" />
          Schedule & Retention
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'backup' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Backup Options */}
            <div className="card p-6">
              <h4 className="text-md font-semibold text-primary mb-4">Backup Options</h4>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Include Datasheets</span>
                    <p className="text-sm text-secondary">Backup all PDF datasheet files</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={includeDatasheets}
                      onChange={(e) => setIncludeDatasheets(e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Include Images</span>
                    <p className="text-sm text-secondary">Backup all part images</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={includeImages}
                      onChange={(e) => setIncludeImages(e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Include Environment File</span>
                    <p className="text-sm text-secondary">Backup .env configuration</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={includeEnv}
                      onChange={(e) => setIncludeEnv(e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="border-t border-border pt-4">
                  <label className="block text-sm font-medium text-primary mb-2">
                    <Lock className="w-4 h-4 inline mr-2" />
                    Encryption Password (optional)
                  </label>
                  <div className="relative">
                    <input
                      type={showBackupPassword ? "text" : "password"}
                      className="input w-full pr-10"
                      placeholder="Enter password to encrypt backup"
                      value={backupPassword}
                      onChange={(e) => setBackupPassword(e.target.value)}
                    />
                    {backupPassword && (
                      <button
                        type="button"
                        onClick={() => setShowBackupPassword(!showBackupPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary hover:text-primary transition-colors"
                      >
                        {showBackupPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-secondary mt-2">
                    {backupPassword
                      ? '🔒 Backup will be encrypted with this password'
                      : '⚠️ Backup will be unencrypted and readable by anyone'}
                  </p>
                </div>
              </div>

              {/* Progress indicator */}
              {activeTaskId && (
                <div className="mt-4 p-4 bg-background-secondary rounded-lg border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-primary">Creating Backup...</span>
                    <span className="text-sm text-secondary">{taskProgress}%</span>
                  </div>
                  <div className="w-full bg-background-tertiary rounded-full h-2 mb-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${taskProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-secondary">{taskStatus}</p>
                </div>
              )}

              <button
                onClick={handleCreateBackup}
                disabled={!!activeTaskId}
                className="btn btn-primary w-full mt-6 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                {activeTaskId ? 'Backup In Progress...' : 'Create Backup Now'}
              </button>
            </div>

            {/* Existing Backups */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-md font-semibold text-primary">Available Backups</h4>
                <button
                  onClick={handleRunRetention}
                  className="btn btn-secondary btn-sm flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Run Retention Cleanup
                </button>
              </div>

              {backupList.length > 0 ? (
                <div className="space-y-2">
                  {backupList.map((backup) => (
                    <div
                      key={backup.filename}
                      className="flex items-center justify-between p-3 bg-background-secondary rounded-lg hover:bg-background-tertiary transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-primary">{backup.filename}</p>
                          {backup.encrypted && <Lock className="w-4 h-4 text-primary" />}
                        </div>
                        <p className="text-sm text-secondary">
                          {backup.size_mb.toFixed(2)} MB • {new Date(backup.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDownloadBackup(backup.filename)}
                          className="btn btn-secondary btn-sm"
                          title="Download backup"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteBackup(backup.filename)}
                          className="btn btn-danger btn-sm"
                          title="Delete backup"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Database className="w-12 h-12 text-muted mx-auto mb-2" />
                  <p className="text-secondary">No backups available</p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'restore' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-6"
          >
            <div className="space-y-6">
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <div className="flex gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <h5 className="font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
                      Important: Restore Process
                    </h5>
                    <ul className="text-sm text-yellow-700 dark:text-yellow-400 space-y-1">
                      <li>• A safety backup will be created before restore begins</li>
                      <li>• Application services will restart after restore completes</li>
                      <li>• All current data will be replaced with backup data</li>
                      <li>• API keys in .env may need to be regenerated for security</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Select Backup File
                </label>
                <input
                  type="file"
                  accept=".zip"
                  className="input w-full"
                  onChange={(e) => setRestoreFile(e.target.files?.[0] || null)}
                />
                {restoreFile && (
                  <p className="text-sm text-secondary mt-2">
                    Selected: {restoreFile.name} ({(restoreFile.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
              </div>

              {restoreFile?.name.includes('_encrypted') && (
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    <Lock className="w-4 h-4 inline mr-2" />
                    Decryption Password
                  </label>
                  <div className="relative">
                    <input
                      type={showRestorePassword ? "text" : "password"}
                      className="input w-full pr-10"
                      placeholder="Enter password to decrypt backup"
                      value={restorePassword}
                      onChange={(e) => setRestorePassword(e.target.value)}
                    />
                    {restorePassword && (
                      <button
                        type="button"
                        onClick={() => setShowRestorePassword(!showRestorePassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary hover:text-primary transition-colors"
                      >
                        {showRestorePassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between p-4 bg-background-secondary rounded-lg">
                <div>
                  <span className="text-primary font-medium">Create Safety Backup</span>
                  <p className="text-sm text-secondary">Backup current data before restore</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={createSafetyBackup}
                    onChange={(e) => setCreateSafetyBackup(e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <button
                onClick={handleRestoreBackup}
                disabled={!restoreFile}
                className="btn btn-primary w-full flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Restore from Backup
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'schedule' && backupConfig && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="card p-6">
              <h4 className="text-md font-semibold text-primary mb-4">Backup Schedule</h4>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Enable Scheduled Backups</span>
                    <p className="text-sm text-secondary">Automatically create backups on schedule</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={backupConfig.schedule_enabled}
                      onChange={(e) => setBackupConfig({
                        ...backupConfig,
                        schedule_enabled: e.target.checked
                      })}
                    />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                {backupConfig.schedule_enabled && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-primary mb-2">
                        Schedule Type
                      </label>
                      <select
                        className="input w-full"
                        value={backupConfig.schedule_type}
                        onChange={(e) => setBackupConfig({
                          ...backupConfig,
                          schedule_type: e.target.value
                        })}
                      >
                        <option value="nightly">Nightly (2:00 AM)</option>
                        <option value="weekly">Weekly (Sunday 2:00 AM)</option>
                        <option value="custom">Custom (Cron Expression)</option>
                      </select>
                    </div>

                    {backupConfig.schedule_type === 'custom' && (
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Cron Expression
                        </label>
                        <input
                          type="text"
                          className="input w-full"
                          placeholder="0 2 * * *"
                          value={backupConfig.schedule_cron || ''}
                          onChange={(e) => setBackupConfig({
                            ...backupConfig,
                            schedule_cron: e.target.value
                          })}
                        />
                        <p className="text-xs text-secondary mt-2">
                          Example: "0 2 * * *" runs at 2:00 AM daily
                        </p>
                      </div>
                    )}

                    {backupConfig.next_backup_at && (
                      <div className="p-4 bg-background-secondary rounded-lg">
                        <div className="flex items-center gap-2 text-primary">
                          <CheckCircle className="w-5 h-5 text-green-500" />
                          <span className="font-medium">Next Backup Scheduled:</span>
                        </div>
                        <p className="text-sm text-secondary mt-1">
                          {new Date(backupConfig.next_backup_at).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="card p-6">
              <h4 className="text-md font-semibold text-primary mb-4">Retention Policy</h4>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Number of Backups to Keep
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    className="input w-full"
                    value={backupConfig.retention_count}
                    onChange={(e) => setBackupConfig({
                      ...backupConfig,
                      retention_count: parseInt(e.target.value) || 7
                    })}
                  />
                  <p className="text-xs text-secondary mt-2">
                    Older backups will be automatically deleted. Current: {backupList.length} backups
                  </p>
                </div>

                <div className="flex items-center justify-between p-4 bg-background-secondary rounded-lg">
                  <div>
                    <span className="text-primary font-medium">Require Encryption</span>
                    <p className="text-sm text-secondary">All backups must be encrypted</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={backupConfig.encryption_required}
                      onChange={(e) => setBackupConfig({
                        ...backupConfig,
                        encryption_required: e.target.checked
                      })}
                    />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                {backupConfig.encryption_required && (
                  <div className="border-t border-border pt-4">
                    <label className="block text-sm font-medium text-primary mb-2">
                      <Lock className="w-4 h-4 inline mr-2" />
                      Scheduled Backup Encryption Password
                    </label>

                    {passwordIsSet && !schedulePassword && (
                      <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                        <p className="text-sm text-green-800 dark:text-green-300 flex items-center gap-2">
                          <CheckCircle className="w-4 h-4" />
                          Password configured for scheduled backups
                        </p>
                        <p className="text-xs text-green-700 dark:text-green-400 mt-1">
                          Enter a new password below to change it, or leave empty to keep current password
                        </p>
                      </div>
                    )}

                    <div className="relative">
                      <input
                        type={showSchedulePassword ? "text" : "password"}
                        className="input w-full pr-10"
                        placeholder={passwordIsSet ? "Enter new password to change (leave empty to keep current)" : "Enter password for automated backups"}
                        value={schedulePassword}
                        onChange={(e) => setSchedulePassword(e.target.value)}
                      />
                      {schedulePassword && (
                        <button
                          type="button"
                          onClick={() => setShowSchedulePassword(!showSchedulePassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary hover:text-primary transition-colors"
                        >
                          {showSchedulePassword ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>

                    {!passwordIsSet && !schedulePassword && (
                      <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
                        ⚠️ No password set - scheduled backups will not be encrypted
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={handleUpdateConfig}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              Save Configuration
            </button>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default BackupManagement
