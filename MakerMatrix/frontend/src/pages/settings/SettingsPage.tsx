import { motion } from 'framer-motion'
import { Settings, User, Bell, Shield, Database, Printer, Palette, Globe, Bot, Save, TestTube, RefreshCw, Upload, FileText, Download, Upload as ImportIcon } from 'lucide-react'
import { useState, useEffect } from 'react'
import { settingsService } from '@/services/settings.service'
import { AIConfig, PrinterConfig, BackupStatus } from '@/types/settings'
import toast from 'react-hot-toast'
import CSVImport from '@/components/ui/CSVImport'

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general')
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null)
  const [printerConfig, setPrinterConfig] = useState<PrinterConfig | null>(null)
  const [backupStatus, setBackupStatus] = useState<BackupStatus | null>(null)
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)

  useEffect(() => {
    if (activeTab === 'ai') {
      loadAIConfig()
    } else if (activeTab === 'printer') {
      loadPrinterConfig()
    } else if (activeTab === 'database') {
      loadBackupStatus()
    }
  }, [activeTab])

  const loadAIConfig = async () => {
    try {
      setLoading(true)
      const config = await settingsService.getAIConfig()
      setAiConfig(config)
      
      // Load models for the current provider
      if (config.provider) {
        await loadAvailableModels()
      }
    } catch (error) {
      toast.error('Failed to load AI configuration')
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableModels = async () => {
    try {
      setLoadingModels(true)
      const models = await settingsService.getAvailableModels()
      setAvailableModels(models)
    } catch (error) {
      toast.error('Failed to load available models')
      setAvailableModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const handleProviderChange = async (newProvider: string) => {
    if (!aiConfig) return
    
    setAiConfig({...aiConfig, provider: newProvider})
    
    // Load models for the new provider
    const tempConfig = {...aiConfig, provider: newProvider}
    setAiConfig(tempConfig)
    await loadAvailableModels()
  }

  const loadPrinterConfig = async () => {
    try {
      setLoading(true)
      const config = await settingsService.getPrinterConfig()
      setPrinterConfig(config)
    } catch (error) {
      toast.error('Failed to load printer configuration')
    } finally {
      setLoading(false)
    }
  }

  const loadBackupStatus = async () => {
    try {
      setLoading(true)
      const status = await settingsService.getBackupStatus()
      setBackupStatus(status)
    } catch (error) {
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
    } catch (error) {
      toast.error('Failed to save AI configuration')
    }
  }

  const testAIConnection = async () => {
    try {
      await settingsService.testAIConnection()
      toast.success('AI connection test successful')
    } catch (error) {
      toast.error('AI connection test failed')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Settings className="w-6 h-6" />
            Settings
          </h1>
          <p className="text-text-secondary mt-1">
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
            { id: 'general', label: 'General', icon: Settings },
            { id: 'import', label: 'Import/Export', icon: ImportIcon },
            { id: 'ai', label: 'AI Helper', icon: Bot },
            { id: 'printer', label: 'Printers', icon: Printer },
            { id: 'database', label: 'Database', icon: Database },
            { id: 'appearance', label: 'Appearance', icon: Palette },
            { id: 'security', label: 'Security', icon: Shield }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-background-secondary'
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
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5" />
              General Settings
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <span className="text-text-primary">Dark Mode</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-primary">Email Notifications</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-primary">Auto-save Changes</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-primary">Show Help Tooltips</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
            
            <div className="border-t border-border pt-6">
              <h4 className="text-md font-medium text-text-primary mb-4">Language & Region</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Language</label>
                  <select className="input w-full">
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Time Zone</label>
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
              <h4 className="text-md font-medium text-text-primary mb-4">Performance</h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-text-primary font-medium">Enable Animations</span>
                    <p className="text-sm text-text-secondary">Smooth transitions and effects</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-text-primary font-medium">Real-time Updates</span>
                    <p className="text-sm text-text-secondary">Live data refresh and notifications</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <Bot className="w-5 h-5" />
                AI Helper Configuration
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={loadAvailableModels}
                  className="btn btn-secondary flex items-center gap-2"
                  disabled={loadingModels}
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
                <button
                  onClick={saveAIConfig}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  Save
                </button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="text-text-secondary mt-2">Loading AI configuration...</p>
              </div>
            ) : aiConfig ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Enabled
                  </label>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer"
                      checked={aiConfig.enabled}
                      onChange={(e) => setAiConfig({...aiConfig, enabled: e.target.checked})}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Provider
                  </label>
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
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    API URL
                  </label>
                  <input
                    type="url"
                    className="input w-full"
                    value={aiConfig.api_url}
                    onChange={(e) => setAiConfig({...aiConfig, api_url: e.target.value})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Model Name
                    {loadingModels && (
                      <span className="ml-2 text-xs text-text-secondary">Loading models...</span>
                    )}
                  </label>
                  {aiConfig.provider === 'ollama' && availableModels.length > 0 ? (
                    <select
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({...aiConfig, model_name: e.target.value})}
                      disabled={loadingModels}
                    >
                      <option value="">Select a model...</option>
                      {availableModels.map((model) => (
                        <option key={model.name} value={model.name}>
                          {model.name}
                          {model.size && ` (${(model.size / 1024 / 1024 / 1024).toFixed(1)}GB)`}
                        </option>
                      ))}
                    </select>
                  ) : aiConfig.provider === 'openai' && availableModels.length > 0 ? (
                    <select
                      className="input w-full"
                      value={aiConfig.model_name}
                      onChange={(e) => setAiConfig({...aiConfig, model_name: e.target.value})}
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
                      onChange={(e) => setAiConfig({...aiConfig, model_name: e.target.value})}
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
                      onChange={(e) => setAiConfig({...aiConfig, model_name: e.target.value})}
                      placeholder="Enter model name manually"
                    />
                  )}
                  {aiConfig.provider === 'ollama' && availableModels.length === 0 && !loadingModels && (
                    <p className="text-xs text-text-secondary mt-1">
                      No models found. Make sure Ollama is running and has models installed.
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Temperature ({aiConfig.temperature})
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    className="w-full"
                    value={aiConfig.temperature}
                    onChange={(e) => setAiConfig({...aiConfig, temperature: parseFloat(e.target.value)})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    className="input w-full"
                    value={aiConfig.max_tokens}
                    onChange={(e) => setAiConfig({...aiConfig, max_tokens: parseInt(e.target.value)})}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    System Prompt
                  </label>
                  <textarea
                    className="input w-full h-32 resize-none"
                    value={aiConfig.system_prompt}
                    onChange={(e) => setAiConfig({...aiConfig, system_prompt: e.target.value})}
                  />
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Bot className="w-12 h-12 text-text-muted mx-auto mb-2" />
                <p className="text-text-secondary">AI configuration not available</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'import' && (
          <div className="space-y-6">
            <CSVImport 
              onImportComplete={(result) => {
                toast.success(`Import completed: ${result.success_parts.length} parts added`)
                if (result.failed_parts.length > 0) {
                  console.log('Failed parts:', result.failed_parts)
                }
              }}
            />
          </div>
        )}

        {activeTab === 'database' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Database className="w-5 h-5" />
              Database Management
            </h3>

            {backupStatus && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{backupStatus.total_records}</p>
                  <p className="text-sm text-text-secondary">Total Records</p>
                </div>
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{(backupStatus.database_size / 1024 / 1024).toFixed(2)} MB</p>
                  <p className="text-sm text-text-secondary">Database Size</p>
                </div>
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{new Date(backupStatus.last_modified).toLocaleDateString()}</p>
                  <p className="text-sm text-text-secondary">Last Modified</p>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={() => settingsService.downloadDatabaseBackup()}
                className="btn btn-primary"
              >
                Download Backup
              </button>
              <button
                onClick={() => settingsService.exportDataJSON()}
                className="btn btn-secondary"
              >
                Export JSON
              </button>
            </div>
          </div>
        )}

        {['printer', 'appearance', 'security'].includes(activeTab) && (
          <div className="text-center py-8">
            <Settings className="w-12 h-12 text-text-muted mx-auto mb-2" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Settings Coming Soon
            </h3>
            <p className="text-text-secondary">
              This section is being developed.
            </p>
          </div>
        )}
      </motion.div>

    </div>
  )
}

export default SettingsPage