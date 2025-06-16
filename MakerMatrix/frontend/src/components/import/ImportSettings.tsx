import React, { useState, useEffect } from 'react'
import { Settings, Download, Image, Save } from 'lucide-react'
import { apiClient } from '@/services/api'
import toast from 'react-hot-toast'

interface ImportConfig {
  download_datasheets: boolean
  download_images: boolean
  overwrite_existing_files: boolean
  download_timeout_seconds: number
  show_progress: boolean
}

const ImportSettings: React.FC = () => {
  const [config, setConfig] = useState<ImportConfig>({
    download_datasheets: true,
    download_images: true,
    overwrite_existing_files: false,
    download_timeout_seconds: 30,
    show_progress: true
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/api/csv/config')
      const data = response.data || response
      if (data) {
        setConfig(data)
      }
    } catch (error) {
      console.error('Failed to load import config:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    try {
      setSaving(true)
      await apiClient.put('/api/csv/config', config)
      toast.success('Configuration saved successfully')
    } catch (error) {
      toast.error('Failed to save configuration')
      console.error('Failed to save import config:', error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="card p-4">
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">
        <h4 className="text-sm font-medium text-primary flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Import Settings
        </h4>
      </div>
      <div className="card-content">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Download Options */}
          <div className="space-y-3">
            <h5 className="text-xs font-medium text-secondary uppercase tracking-wide">Download Options</h5>
            
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={config.download_datasheets}
                onChange={(e) => setConfig(prev => ({ ...prev, download_datasheets: e.target.checked }))}
                className="checkbox"
              />
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-secondary" />
                <span className="text-sm text-primary">Download datasheets</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={config.download_images}
                onChange={(e) => setConfig(prev => ({ ...prev, download_images: e.target.checked }))}
                className="checkbox"
              />
              <div className="flex items-center gap-2">
                <Image className="w-4 h-4 text-secondary" />
                <span className="text-sm text-primary">Download images</span>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={config.overwrite_existing_files}
                onChange={(e) => setConfig(prev => ({ ...prev, overwrite_existing_files: e.target.checked }))}
                className="checkbox"
              />
              <span className="text-sm text-primary">Overwrite existing files</span>
            </label>
          </div>

          {/* Performance Options */}
          <div className="space-y-3">
            <h5 className="text-xs font-medium text-secondary uppercase tracking-wide">Options</h5>
            
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_progress}
                onChange={(e) => setConfig(prev => ({ ...prev, show_progress: e.target.checked }))}
                className="checkbox"
              />
              <span className="text-sm text-primary">Show import progress</span>
            </label>

            <div className="space-y-2">
              <label className="block text-xs font-medium text-primary">
                Download timeout: {config.download_timeout_seconds}s
              </label>
              <input
                type="range"
                min="10"
                max="120"
                step="10"
                value={config.download_timeout_seconds}
                onChange={(e) => setConfig(prev => ({ ...prev, download_timeout_seconds: parseInt(e.target.value) }))}
                className="w-full"
              />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={saveConfig}
            disabled={saving}
            className="btn btn-primary flex items-center gap-2"
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ImportSettings