import { motion } from 'framer-motion'
import {
  Settings,
  Shield,
  Database,
  Printer,
  Palette,
  Globe,
  Bot,
  Save,
  TestTube,
  RefreshCw,
  Upload as ImportIcon,
  Activity,
  Plus,
  Monitor,
  Sun,
  Moon,
  FileText,
} from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { settingsService } from '@/services/settings.service'
import type { AIConfig } from '@/types/settings'
import toast from 'react-hot-toast'
import ImportSelector from '@/components/import/ImportSelector'
import TasksManagement from '@/components/tasks/TasksManagement'
import ThemeSelector from '@/components/ui/ThemeSelector'
import { useTheme } from '@/contexts/ThemeContext'
import { SupplierConfigPage } from '@/pages/suppliers/SupplierConfigPage'
import DynamicPrinterModal from '@/components/printer/DynamicPrinterModal'
import Templates from '@/pages/Templates'
import ApiKeyManagement from '@/components/settings/ApiKeyManagement'
import BackupManagement from '@/components/settings/BackupManagement'
import { usePermissions } from '@/hooks/usePermissions'

const SettingsPage = () => {
  const { isDarkMode, toggleDarkMode, isCompactMode, toggleCompactMode } = useTheme()
  const { isAdmin } = usePermissions()
  const isDebugMode = import.meta.env.VITE_DEBUG === 'true'
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'general')
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null)
  const [availableModels, setAvailableModels] = useState<
    Array<{ name: string; size?: string; description?: string }>
  >([])
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)
  const [availablePrinters, setAvailablePrinters] = useState<
    Array<{
      printer_id: string
      name: string
      model: string
      status?: string
      driver_type?: string
      backend?: string
    }>
  >([])
  const [showPrinterModal, setShowPrinterModal] = useState(false)
  const [printerModalMode, setPrinterModalMode] = useState<'add' | 'edit'>('add')
  const [selectedPrinterForEdit, setSelectedPrinterForEdit] = useState<{
    printer_id: string
    name: string
    model: string
    driver_type: string
    backend: string
    identifier: string
    dpi: number
    scaling_factor: number
  } | null>(null)

  const loadAvailableModels = useCallback(
    async (configOverride?: AIConfig | null) => {
      const targetConfig = configOverride ?? aiConfig

      if (!targetConfig?.enabled) {
        setAvailableModels([])
        return
      }

      try {
        setLoadingModels(true)
        const response = await settingsService.getAvailableModels()
        const models = response.data?.models || []
        setAvailableModels(models)

        if (response.status === 'warning') {
          toast(response.message || 'AI models loaded with warnings', { icon: '⚠️' })
        } else if (response.status === 'error') {
          toast.error(response.message || 'Failed to load available models')
          setAvailableModels([])
        }
      } catch (_error) {
        toast.error('Failed to load available models')
        setAvailableModels([])
      } finally {
        setLoadingModels(false)
      }
    },
    [aiConfig]
  )

  const loadAIConfig = useCallback(async () => {
    try {
      setLoading(true)
      const config = await settingsService.getAIConfig()
      setAiConfig(config)

      // Load models for the current provider
      if (config.provider && config.enabled) {
        await loadAvailableModels(config)
      } else {
        setAvailableModels([])
      }
    } catch (_error) {
      toast.error('Failed to load AI configuration')
    } finally {
      setLoading(false)
    }
  }, [loadAvailableModels])

  useEffect(() => {
    if (activeTab === 'ai') {
      loadAIConfig()
    } else if (activeTab === 'printer') {
      loadPrinters()
    } else if (activeTab === 'database') {
      loadBackupStatus()
    }
  }, [activeTab, loadAIConfig])

  const handleProviderChange = async (newProvider: string) => {
    if (!aiConfig) return

    setAiConfig({ ...aiConfig, provider: newProvider })

    // Load models for the new provider
    const tempConfig = { ...aiConfig, provider: newProvider }
    setAiConfig(tempConfig)
    await loadAvailableModels(tempConfig)
  }

  const loadPrinters = async () => {
    try {
      setLoading(true)
      const printers = await settingsService.getAvailablePrinters()
      setAvailablePrinters(printers)
    } catch (error) {
      console.error('Load printers error:', error)
      toast.error('Failed to load printers')
    } finally {
      setLoading(false)
    }
  }

  const handlePrinterModalSuccess = async () => {
    await loadPrinters()
    setShowPrinterModal(false)
    setSelectedPrinterForEdit(null)
  }

  const loadBackupStatus = async () => {
    try {
      setLoading(true)
      await settingsService.getBackupStatus()
    } catch (_error) {
      toast.error('Failed to load backup status')
    } finally {
      setLoading(false)
    }
  }

  const saveAIConfig = async () => {
    if (!aiConfig) return

    try {
      await settingsService.updateAIConfig(aiConfig)
      toast.success('AI configuration saved successfully')
    } catch (_error) {
      toast.error('Failed to save AI configuration')
    }
  }

  const testAIConnection = async () => {
    try {
      const response = await settingsService.testAIConnection()

      if (response.status === 'success') {
        toast.success(response.message || 'AI connection test successful')
      } else if (response.status === 'warning') {
        toast(response.message || 'AI connection test returned warnings', { icon: '⚠️' })
      } else {
        toast.error(response.message || 'AI connection test failed')
      }
    } catch (_error) {
      toast.error('AI connection test failed')
    }
  }

  return (
    <div className="max-w-screen-2xl space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Settings className="w-6 h-6" />
            Settings
          </h1>
          <p className="text-secondary mt-1">
            Configure application preferences and system settings
          </p>
        </div>
      </motion.div>

      {/* Settings Navigation */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-1"
      >
        <div className="flex flex-wrap gap-1">
          {[
            { id: 'general', label: 'General', icon: Settings, adminOnly: false },
            { id: 'import', label: 'Import/Export', icon: ImportIcon, adminOnly: true },
            { id: 'tasks', label: 'Background Tasks', icon: Activity, adminOnly: true },
            { id: 'ai', label: 'AI Helper', icon: Bot, adminOnly: true },
            { id: 'suppliers', label: 'Suppliers', icon: Globe, adminOnly: true },
            { id: 'printer', label: 'Printers', icon: Printer, adminOnly: true },
            { id: 'templates', label: 'Label Templates', icon: FileText, adminOnly: true },
            { id: 'database', label: 'Database', icon: Database, adminOnly: true },
            { id: 'appearance', label: 'Appearance', icon: Palette, adminOnly: false },
            { id: 'security', label: 'Security', icon: Shield, adminOnly: false },
          ]
            .filter((tab) => !tab.adminOnly || isAdmin())
            .map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors font-medium ${
                  activeTab === tab.id
                    ? 'bg-primary-20 text-primary border border-primary shadow-lg font-semibold'
                    : 'text-secondary hover:text-primary hover:bg-background-secondary border border-border bg-background-primary'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
        </div>
      </motion.div>

      {/* Settings Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="card p-6"
      >
        {activeTab === 'general' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-primary mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5" />
              General Settings
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-primary font-medium">Auto-save Changes</span>
                  <p className="text-sm text-secondary">Automatically save form changes</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-primary font-medium">Sound Effects</span>
                  <p className="text-sm text-secondary">Play sounds for notifications</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>

            <div className="border-t border-border pt-6">
              <h4 className="text-md font-medium text-primary mb-4">Language & Region</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Language</label>
                  <select className="input w-full">
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Time Zone</label>
                  <select className="input w-full">
                    <option value="UTC">UTC</option>
                    <option value="EST">Eastern Time</option>
                    <option value="PST">Pacific Time</option>
                    <option value="GMT">Greenwich Mean Time</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="border-t border-border pt-6">
              <h4 className="text-md font-medium text-primary mb-4">Data & Performance</h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Real-time Updates</span>
                    <p className="text-sm text-secondary">Live data refresh and notifications</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Background Sync</span>
                    <p className="text-sm text-secondary">Sync data when app is in background</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                <Bot className="w-5 h-5" />
                AI Helper Configuration
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => loadAvailableModels()}
                  className="btn btn-secondary flex items-center gap-2"
                  disabled={loadingModels || !aiConfig?.enabled}
                >
                  <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
                  Refresh Models
                </button>
                <button
                  onClick={testAIConnection}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <TestTube className="w-4 h-4" />
                  Test Connection
                </button>
                <button onClick={saveAIConfig} className="btn btn-primary flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  Save
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="text-secondary mt-2">Loading AI configuration...</p>
              </div>
            ) : aiConfig ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Enabled</label>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={aiConfig.enabled}
                      onChange={(e) => setAiConfig({ ...aiConfig, enabled: e.target.checked })}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Provider</label>
                  <select
                    className="input w-full"
                    value={aiConfig.provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="ollama">Ollama</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">API URL</label>
                  <input
                    type="url"
                    className="input w-full"
                    value={aiConfig.api_url}
                    onChange={(e) => setAiConfig({ ...aiConfig, api_url: e.target.value })}
                  />
                </div>

                {(aiConfig.provider === 'openai' || aiConfig.provider === 'anthropic') && (
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">API Key</label>
                    <input
                      type="password"
                      className="input w-full"
                      value={aiConfig.api_key || ''}
                      onChange={(e) => setAiConfig({ ...aiConfig, api_key: e.target.value })}
                      placeholder={`Enter your ${aiConfig.provider === 'openai' ? 'OpenAI' : 'Anthropic'} API key`}
                    />
                    <p className="text-xs text-secondary mt-1">
                      {aiConfig.provider === 'openai'
                        ? 'Get your API key from platform.openai.com'
                        : 'Get your API key from console.anthropic.com'}
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Model Name
                    {loadingModels && (
                      <span className="ml-2 text-xs text-secondary">Loading models...</span>
                    )}
                  </label>
                  {aiConfig.provider === 'ollama' && availableModels.length > 0 ? (
                    <select
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({ ...aiConfig, model_name: e.target.value })}
                      disabled={loadingModels}
                    >
                      <option value="">Select a model...</option>
                      {availableModels.map((model) => (
                        <option key={model.name} value={model.name}>
                          {model.name}
                          {model.size && typeof model.size === 'string'
                            ? ` (${model.size})`
                            : ''}
                        </option>
                      ))}
                    </select>
                  ) : aiConfig.provider === 'openai' && availableModels.length > 0 ? (
                    <select
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({ ...aiConfig, model_name: e.target.value })}
                    >
                      <option value="">Select a model...</option>
                      {availableModels.map((model) => (
                        <option key={model.name} value={model.name}>
                          {model.name}
                          {model.description && ` - ${model.description}`}
                        </option>
                      ))}
                    </select>
                  ) : aiConfig.provider === 'anthropic' && availableModels.length > 0 ? (
                    <select
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({ ...aiConfig, model_name: e.target.value })}
                    >
                      <option value="">Select a model...</option>
                      {availableModels.map((model) => (
                        <option key={model.name} value={model.name}>
                          {model.name}
                          {model.description && ` - ${model.description}`}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({ ...aiConfig, model_name: e.target.value })}
                      placeholder="Enter model name manually"
                    />
                  )}
                  {aiConfig.provider === 'ollama' &&
                    availableModels.length === 0 &&
                    !loadingModels && (
                      <p className="text-xs text-secondary mt-1">
                        No models found. Make sure Ollama is running and has models installed.
                      </p>
                    )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
                    Temperature ({aiConfig.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    className="w-full"
                    value={aiConfig.temperature}
                    onChange={(e) =>
                      setAiConfig({ ...aiConfig, temperature: parseFloat(e.target.value) })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">Max Tokens</label>
                  <input
                    type="number"
                    className="input w-full"
                    value={aiConfig.max_tokens}
                    onChange={(e) =>
                      setAiConfig({ ...aiConfig, max_tokens: parseInt(e.target.value) })
                    }
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-primary mb-2">
                    System Prompt
                  </label>
                  <textarea
                    className="input w-full h-32 resize-none"
                    value={aiConfig.system_prompt}
                    onChange={(e) => setAiConfig({ ...aiConfig, system_prompt: e.target.value })}
                  />
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Bot className="w-12 h-12 text-muted mx-auto mb-2" />
                <p className="text-secondary">AI configuration not available</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'import' && (
          <div className="space-y-6">
            <ImportSelector
              onImportComplete={(result) => {
                toast.success(`Import completed: ${result.success_parts.length} parts added`)
                if (result.failed_parts.length > 0) {
                  console.log('Failed parts:', result.failed_parts)
                }
              }}
            />
          </div>
        )}

        {activeTab === 'tasks' && <TasksManagement />}

        {activeTab === 'suppliers' && <SupplierConfigPage />}

        {activeTab === 'database' && <BackupManagement />}

        {activeTab === 'printer' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                <Printer className="w-5 h-5" />
                Printer Management
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setPrinterModalMode('add')
                    setSelectedPrinterForEdit(null)
                    setShowPrinterModal(true)
                  }}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Printer
                </button>
                {isDebugMode && (
                  <button
                    onClick={async () => {
                      await settingsService.registerPrinter({
                        printer_id: 'debug_brother',
                        name: 'Debug Brother QL',
                        driver_type: 'brother_ql',
                        model: 'QL-800',
                        backend: 'network',
                        identifier: 'tcp://192.168.1.71:9100',
                        dpi: 300,
                        scaling_factor: 1.1,
                      })
                      toast.success('Debug printer added!')
                      await loadPrinters()
                    }}
                    className="btn btn-secondary flex items-center gap-2"
                  >
                    🔧 Add Debug Printer
                  </button>
                )}
                <button
                  onClick={loadPrinters}
                  className="btn btn-secondary flex items-center gap-2"
                  disabled={loading}
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="text-secondary mt-2">Loading printers...</p>
              </div>
            ) : availablePrinters.length > 0 ? (
              <div className="space-y-6">
                {/* Printer List */}
                <div className="grid gap-4">
                  {availablePrinters.map((printer) => (
                    <div
                      key={printer.printer_id}
                      className="border border-border rounded-lg p-4 bg-background-secondary"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-primary">{printer.name}</h4>
                          <p className="text-sm text-secondary">{printer.model}</p>
                          <div className="flex items-center gap-4 mt-2">
                            <span
                              className={`inline-block px-2 py-1 rounded text-xs ${
                                printer.status === 'available' || printer.status === 'ready'
                                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                              }`}
                            >
                              {printer.status}
                            </span>
                            <span className="text-xs text-secondary">ID: {printer.printer_id}</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={async () => {
                              try {
                                const result = await settingsService.testPrinterConnection(
                                  printer.printer_id
                                )

                                if (result.success) {
                                  toast.success('✅ Printer connection successful!')
                                } else {
                                  toast.error(`❌ Connection test failed: ${result.message}`)
                                }
                              } catch (_error) {
                                toast.error('Failed to test printer connection')
                              }
                            }}
                            className="btn btn-secondary btn-sm"
                          >
                            🧪 Test
                          </button>
                          <button
                            onClick={() => {
                              setPrinterModalMode('edit')
                              // Ensure all required fields are present
                              setSelectedPrinterForEdit({
                                printer_id: printer.printer_id,
                                name: printer.name,
                                model: printer.model,
                                driver_type: printer.driver_type || 'brother_ql',
                                backend: printer.backend || 'network',
                                identifier: '',
                                dpi: 300,
                                scaling_factor: 1.0,
                              })
                              setShowPrinterModal(true)
                            }}
                            className="btn btn-secondary btn-sm"
                          >
                            ✏️ Edit
                          </button>
                          <button
                            onClick={async () => {
                              if (
                                confirm(
                                  `Are you sure you want to delete printer "${printer.name}"?`
                                )
                              ) {
                                try {
                                  await settingsService.deletePrinter(printer.printer_id)
                                  toast.success('✅ Printer deleted successfully!')
                                  await loadPrinters()
                                } catch (error) {
                                  console.error('Delete printer error:', error)
                                  toast.error('❌ Failed to delete printer')
                                }
                              }
                            }}
                            className="btn btn-danger btn-sm"
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Printer className="w-12 h-12 text-muted mx-auto mb-2" />
                <h3 className="text-lg font-semibold text-primary mb-2">No Printers Registered</h3>
                <p className="text-secondary mb-4">
                  Add your Brother QL label printer to start printing labels.
                </p>
                <button
                  onClick={() => {
                    setPrinterModalMode('add')
                    setSelectedPrinterForEdit(null)
                    setShowPrinterModal(true)
                  }}
                  className="btn btn-primary"
                >
                  Add Your First Printer
                </button>
              </div>
            )}

            {/* Dynamic Printer Modal */}
            <DynamicPrinterModal
              isOpen={showPrinterModal}
              onClose={() => {
                setShowPrinterModal(false)
                setSelectedPrinterForEdit(null)
              }}
              mode={printerModalMode}
              existingPrinter={selectedPrinterForEdit}
              onSuccess={handlePrinterModalSuccess}
            />
          </div>
        )}

        {activeTab === 'appearance' && (
          <div className="space-y-8">
            <h3 className="text-lg font-semibold text-primary mb-4 flex items-center gap-2">
              <Palette className="w-5 h-5" />
              Appearance Settings
            </h3>

            {/* Dark Mode Section */}
            <div className="space-y-4">
              <h4 className="text-md font-medium text-primary">Display Mode</h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <button
                  onClick={() => {
                    // Auto mode logic would go here
                    console.log('Auto mode selected')
                  }}
                  className="flex flex-col items-center gap-3 p-4 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-all"
                >
                  <Monitor className="w-8 h-8 text-secondary" />
                  <div className="text-center">
                    <div className="font-medium text-primary">Auto</div>
                    <div className="text-sm text-secondary">Follow system</div>
                  </div>
                </button>

                <button
                  onClick={() => isDarkMode && toggleDarkMode()}
                  className={`flex flex-col items-center gap-3 p-4 rounded-lg border transition-all ${
                    !isDarkMode
                      ? 'border-primary bg-primary-10 text-primary'
                      : 'border-border hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <Sun className="w-8 h-8" />
                  <div className="text-center">
                    <div className="font-medium">Light</div>
                    <div className="text-sm opacity-70">Bright theme</div>
                  </div>
                </button>

                <button
                  onClick={() => !isDarkMode && toggleDarkMode()}
                  className={`flex flex-col items-center gap-3 p-4 rounded-lg border transition-all ${
                    isDarkMode
                      ? 'border-primary bg-primary-10 text-primary'
                      : 'border-border hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <Moon className="w-8 h-8" />
                  <div className="text-center">
                    <div className="font-medium">Dark</div>
                    <div className="text-sm opacity-70">Easy on eyes</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Theme Selection Section */}
            <div className="space-y-4 border-t border-border pt-6">
              <h4 className="text-md font-medium text-primary">Color Theme</h4>
              <p className="text-sm text-secondary mb-4">
                Choose a color theme that suits your preference
              </p>
              <ThemeSelector />
            </div>

            {/* Compact Mode Section */}
            <div className="space-y-4 border-t border-border pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-md font-medium text-primary">Compact Mode</h4>
                  <p className="text-sm text-secondary">
                    Reduce spacing and padding for more content density
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={isCompactMode}
                    onChange={toggleCompactMode}
                  />
                  <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'templates' && <Templates />}

        {activeTab === 'security' && <ApiKeyManagement />}
      </motion.div>
    </div>
  )
}

export default SettingsPage
