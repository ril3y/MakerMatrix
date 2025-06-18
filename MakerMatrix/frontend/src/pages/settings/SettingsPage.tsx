import { motion } from 'framer-motion'
import { Settings, Shield, Database, Printer, Palette, Globe, Bot, Save, TestTube, RefreshCw, Upload as ImportIcon, Activity, Plus, X, Monitor, Sun, Moon } from 'lucide-react'
import { useState, useEffect } from 'react'
import { settingsService } from '@/services/settings.service'
import { AIConfig, PrinterConfig, BackupStatus } from '@/types/settings'
import toast from 'react-hot-toast'
import ImportSelector from '@/components/import/ImportSelector'
import TasksManagement from '@/components/tasks/TasksManagement'
import ThemeSelector from '@/components/ui/ThemeSelector'
import { useTheme } from '@/contexts/ThemeContext'
import { SupplierConfigPage } from '@/pages/suppliers/SupplierConfigPage'

const SettingsPage = () => {
  const { isDarkMode, toggleDarkMode, currentTheme, setTheme, isCompactMode, toggleCompactMode } = useTheme()
  const [activeTab, setActiveTab] = useState('general')
  const [aiConfig, setAiConfig] = useState<AIConfig | null>(null)
  const [backupStatus, setBackupStatus] = useState<BackupStatus | null>(null)
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)
  const [availablePrinters, setAvailablePrinters] = useState<any[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<string>('')
  const [printerInfo, setPrinterInfo] = useState<any>(null)
  const [testLabelText, setTestLabelText] = useState('MakerMatrix Test Label')
  const [selectedLabelSize, setSelectedLabelSize] = useState('12mm')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [labelTemplate, setLabelTemplate] = useState('{part_name}')
  const [labelLength, setLabelLength] = useState(39)
  const [fitToLabel, setFitToLabel] = useState(true)
  const [includeQR, setIncludeQR] = useState(false)
  const [qrData, setQrData] = useState('part_number')
  const [showAddPrinter, setShowAddPrinter] = useState(false)
  const [newPrinter, setNewPrinter] = useState({
    printer_id: '',
    name: '',
    driver_type: 'brother_ql',
    model: 'QL-800',
    backend: 'network',
    identifier: '',
    dpi: 300,
    scaling_factor: 1.1
  })
  const [supportedDrivers, setSupportedDrivers] = useState<any[]>([])
  const [discoveredPrinters, setDiscoveredPrinters] = useState<any[]>([])
  const [testingSetup, setTestingSetup] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)

  useEffect(() => {
    if (activeTab === 'ai') {
      loadAIConfig()
    } else if (activeTab === 'printer') {
      loadPrinters()
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

  const loadPrinters = async () => {
    try {
      setLoading(true)
      const printers = await settingsService.getAvailablePrinters()
      setAvailablePrinters(printers)
      
      // Auto-select first printer if available
      if (printers.length > 0 && !selectedPrinter) {
        setSelectedPrinter(printers[0].printer_id)
        await loadPrinterInfo(printers[0].printer_id)
      }
    } catch (error) {
      toast.error('Failed to load printers')
    } finally {
      setLoading(false)
    }
  }

  const loadPrinterInfo = async (printerId: string) => {
    try {
      const info = await settingsService.getPrinterInfo(printerId)
      setPrinterInfo(info)
      
      // Set default label size if available
      if (info.supported_sizes && info.supported_sizes.length > 0) {
        // Prefer "12mm" if available, then "12", otherwise use the first size
        const defaultSize = info.supported_sizes.find((s: any) => s.name === '12mm') || 
                           info.supported_sizes.find((s: any) => s.name === '12') || 
                           info.supported_sizes[0]
        setSelectedLabelSize(defaultSize.name)
      }
    } catch (error) {
      toast.error('Failed to load printer information')
    }
  }

  const handlePrinterChange = async (printerId: string) => {
    setSelectedPrinter(printerId)
    await loadPrinterInfo(printerId)
  }

  const testPrinterConnection = async () => {
    if (!selectedPrinter) return
    
    try {
      const result = await settingsService.testPrinterConnection(selectedPrinter)
      if (result.success) {
        toast.success(`✅ ${result.message}`)
      } else {
        toast.error(`❌ Connection test failed`)
      }
    } catch (error) {
      toast.error('Failed to test printer connection')
    }
  }

  const processLabelTemplate = (template: string, testData?: any) => {
    // Use test data or default values for placeholders
    const data = testData || {
      part_name: testLabelText || 'Test Part',
      part_number: 'TP-001',
      location: 'A1-B2',
      category: 'Electronics',
      quantity: '10'
    }
    
    let processed = template
    
    // Replace standard placeholders
    Object.entries(data).forEach(([key, value]) => {
      processed = processed.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value))
    })
    
    // Handle QR code placeholders
    const qrMatch = processed.match(/\{qr=([^}]+)\}/)
    if (qrMatch) {
      const qrData = qrMatch[1]
      // For now, replace QR with [QR] text - backend will handle actual QR generation
      processed = processed.replace(/\{qr=[^}]+\}/g, `[QR:${data[qrData as keyof typeof data] || qrData}]`)
    }
    
    return processed
  }

  const printTestLabel = async () => {
    if (!selectedPrinter) return
    
    try {
      // Create test data for the template
      const testData = {
        part_name: testLabelText || 'Test Part',
        part_number: 'TP-001',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10'
      }
      
      const requestData = {
        printer_id: selectedPrinter,
        template: labelTemplate,
        text: "", // Not used anymore
        label_size: selectedLabelSize,
        label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
        options: {
          fit_to_label: fitToLabel,
          include_qr: includeQR,
          qr_data: includeQR ? qrData : undefined
        },
        data: testData
      }
      
      const result = await settingsService.printAdvancedLabel(requestData)
      if (result.success) {
        toast.success('✅ Test label printed successfully!')
      } else {
        toast.error(`❌ Print failed: ${result.error}`)
      }
    } catch (error) {
      toast.error('Failed to print test label')
    }
  }

  const generatePreview = async () => {
    try {
      // Create test data for the template
      const testData = {
        part_name: testLabelText || 'Test Part',
        part_number: 'TP-001',
        location: 'A1-B2',
        category: 'Electronics',
        quantity: '10'
      }
      
      const requestData = {
        template: labelTemplate,
        text: "", // Not used anymore
        label_size: selectedLabelSize,
        label_length: selectedLabelSize.includes('mm') ? labelLength : undefined,
        options: {
          fit_to_label: fitToLabel,
          include_qr: includeQR,
          qr_data: includeQR ? qrData : undefined
        },
        data: testData
      }
      
      const blob = await settingsService.previewAdvancedLabel(requestData)
      const url = URL.createObjectURL(blob)
      setPreviewUrl(url)
    } catch (error) {
      toast.error('Failed to generate preview')
    }
  }

  const handleAddPrinter = async () => {
    try {
      if (!newPrinter.printer_id || !newPrinter.name || !newPrinter.identifier) {
        toast.error('Please fill in all required fields')
        return
      }
      
      await settingsService.registerPrinter(newPrinter)
      toast.success('Printer registered successfully!')
      
      // Reset form and reload printers
      setNewPrinter({
        printer_id: '',
        name: '',
        driver_type: 'brother_ql',
        model: 'QL-800',
        backend: 'network',
        identifier: '',
        dpi: 300,
        scaling_factor: 1.1
      })
      setShowAddPrinter(false)
      setTestResult(null)
      await loadPrinters()
    } catch (error) {
      toast.error('Failed to register printer')
    }
  }

  const loadSupportedDrivers = async () => {
    try {
      const drivers = await settingsService.getSupportedDrivers()
      setSupportedDrivers(drivers)
    } catch (error) {
      console.error('Failed to load supported drivers:', error)
    }
  }

  const discoverPrinters = async () => {
    try {
      setLoading(true)
      const result = await settingsService.discoverPrinters()
      setDiscoveredPrinters(result.discovered_printers || [])
      toast.success(`Discovery complete: ${result.message}`)
    } catch (error) {
      toast.error('Printer discovery failed')
    } finally {
      setLoading(false)
    }
  }

  const testPrinterSetup = async () => {
    try {
      setTestingSetup(true)
      const result = await settingsService.testPrinterSetup(newPrinter)
      setTestResult(result)
      
      if (result.success) {
        toast.success('✅ Connection test successful!')
        // Apply recommendations
        if (result.recommendations) {
          setNewPrinter(prev => ({
            ...prev,
            scaling_factor: result.recommendations.scaling_factor || prev.scaling_factor
          }))
        }
      } else {
        toast.error(`❌ Connection test failed: ${result.message}`)
      }
    } catch (error) {
      toast.error('Test setup failed')
      setTestResult({ success: false, message: 'Test failed' })
    } finally {
      setTestingSetup(false)
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
            { id: 'general', label: 'General', icon: Settings },
            { id: 'import', label: 'Import/Export', icon: ImportIcon },
            { id: 'tasks', label: 'Background Tasks', icon: Activity },
            { id: 'ai', label: 'AI Helper', icon: Bot },
            { id: 'suppliers', label: 'Suppliers', icon: Globe },
            { id: 'printer', label: 'Printers', icon: Printer },
            { id: 'database', label: 'Database', icon: Database },
            { id: 'appearance', label: 'Appearance', icon: Palette },
            { id: 'security', label: 'Security', icon: Shield }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors font-medium ${
                activeTab === tab.id
                  ? 'bg-primary text-white border border-primary shadow-lg font-semibold'
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
                <p className="text-secondary mt-2">Loading AI configuration...</p>
              </div>
            ) : aiConfig ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
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
                  <label className="block text-sm font-medium text-primary mb-2">
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
                  <label className="block text-sm font-medium text-primary mb-2">
                    API URL
                  </label>
                  <input
                    type="url"
                    className="input w-full"
                    value={aiConfig.api_url}
                    onChange={(e) => setAiConfig({...aiConfig, api_url: e.target.value})}
                  />
                </div>

                {(aiConfig.provider === 'openai' || aiConfig.provider === 'anthropic') && (
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      API Key
                    </label>
                    <input
                      type="password"
                      className="input w-full"
                      value={aiConfig.api_key || ''}
                      onChange={(e) => setAiConfig({...aiConfig, api_key: e.target.value})}
                      placeholder={`Enter your ${aiConfig.provider === 'openai' ? 'OpenAI' : 'Anthropic'} API key`}
                    />
                    <p className="text-xs text-secondary mt-1">
                      {aiConfig.provider === 'openai' 
                        ? 'Get your API key from platform.openai.com' 
                        : 'Get your API key from console.anthropic.com'
                      }
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
                    onChange={(e) => setAiConfig({...aiConfig, temperature: parseFloat(e.target.value)})}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary mb-2">
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
                  <label className="block text-sm font-medium text-primary mb-2">
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

        {activeTab === 'tasks' && (
          <TasksManagement />
        )}

        {activeTab === 'database' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
              <Database className="w-5 h-5" />
              Database Management
            </h3>

            {backupStatus && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{backupStatus.total_records}</p>
                  <p className="text-sm text-secondary">Total Records</p>
                </div>
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{(backupStatus.database_size / 1024 / 1024).toFixed(2)} MB</p>
                  <p className="text-sm text-secondary">Database Size</p>
                </div>
                <div className="text-center p-4 bg-background-secondary rounded-lg">
                  <p className="text-2xl font-bold text-primary">{new Date(backupStatus.last_modified).toLocaleDateString()}</p>
                  <p className="text-sm text-secondary">Last Modified</p>
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
                    setShowAddPrinter(true)
                    loadSupportedDrivers()
                  }}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Printer
                </button>
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
                      scaling_factor: 1.1
                    })
                    toast.success('Debug printer added!')
                    await loadPrinters()
                  }}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  🔧 Add Debug Printer
                </button>
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
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Printer Selection */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Select Printer
                    </label>
                    <select
                      className="input w-full"
                      value={selectedPrinter}
                      onChange={(e) => handlePrinterChange(e.target.value)}
                    >
                      {availablePrinters.map((printer) => (
                        <option key={printer.printer_id} value={printer.printer_id}>
                          {printer.name} ({printer.model})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Printer Information */}
                  {printerInfo && (
                    <div className="bg-background-secondary rounded-lg p-4 space-y-3">
                      <h4 className="font-medium text-primary">Printer Details</h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-secondary">Name:</span>
                          <span className="text-primary ml-2">{printerInfo.name}</span>
                        </div>
                        <div>
                          <span className="text-secondary">Model:</span>
                          <span className="text-primary ml-2">{printerInfo.model}</span>
                        </div>
                        <div>
                          <span className="text-secondary">Status:</span>
                          <span className={`ml-2 px-2 py-1 rounded text-xs ${
                            printerInfo.status === 'ready' 
                              ? 'bg-success/20 text-success' 
                              : 'bg-error/20 text-error'
                          }`}>
                            {printerInfo.status}
                          </span>
                        </div>
                        <div>
                          <span className="text-secondary">Capabilities:</span>
                          <span className="text-primary ml-2">{printerInfo.capabilities?.join(', ')}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Label Design Controls */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-primary mb-2">
                        Label Template
                      </label>
                      <textarea
                        className="input w-full h-20 resize-none"
                        value={labelTemplate}
                        onChange={(e) => setLabelTemplate(e.target.value)}
                        placeholder="Use {part_name}, {part_number}, {qr=part_number}, etc."
                      />
                      <p className="text-xs text-secondary mt-1">
                        Available placeholders: {'{part_name}'}, {'{part_number}'}, {'{qr=data}'}, {'{location}'}, {'{category}'}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Label Size
                        </label>
                        <select 
                          className="input w-full"
                          value={selectedLabelSize}
                          onChange={(e) => setSelectedLabelSize(e.target.value)}
                        >
                          {printerInfo?.supported_sizes?.map((size: any) => (
                            <option key={size.name} value={size.name}>
                              {size.name} - {size.width_mm}mm {size.height_mm ? `x ${size.height_mm}mm` : '(continuous)'}
                            </option>
                          ))}
                          {!printerInfo?.supported_sizes && (
                            <option disabled>No printer selected</option>
                          )}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Label Length (mm)
                        </label>
                        <input
                          type="number"
                          min="20"
                          max="200"
                          className="input w-full"
                          value={labelLength}
                          onChange={(e) => setLabelLength(Number(e.target.value))}
                          disabled={selectedLabelSize && !selectedLabelSize.includes('mm')}
                        />
                        <p className="text-xs text-secondary mt-1">
                          {selectedLabelSize && !selectedLabelSize.includes('mm') ? 'Fixed size label' : 'Length for continuous labels'}
                        </p>
                      </div>
                    </div>

                    {/* Label Options */}
                    <div className="bg-background-secondary rounded-lg p-3 space-y-3">
                      <h5 className="font-medium text-primary">Label Options</h5>
                      
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={fitToLabel}
                            onChange={(e) => setFitToLabel(e.target.checked)}
                            className="w-4 h-4 text-primary bg-background-primary border-border rounded focus:ring-primary"
                          />
                          <span className="text-sm text-primary">Fit text to label</span>
                        </label>
                      </div>

                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={includeQR}
                            onChange={(e) => setIncludeQR(e.target.checked)}
                            className="w-4 h-4 text-primary bg-background-primary border-border rounded focus:ring-primary"
                          />
                          <span className="text-sm text-primary">Include QR Code</span>
                        </label>
                      </div>

                      {includeQR && (
                        <div>
                          <label className="block text-xs font-medium text-primary mb-1">
                            QR Code Data
                          </label>
                          <input
                            type="text"
                            className="input w-full text-sm"
                            value={qrData}
                            onChange={(e) => setQrData(e.target.value)}
                            placeholder="part_number, part_name, or custom text"
                          />
                        </div>
                      )}
                    </div>


                    <div className="flex gap-2">
                      <button
                        onClick={testPrinterConnection}
                        className="btn btn-secondary flex items-center gap-2 flex-1"
                        disabled={!selectedPrinter}
                      >
                        <TestTube className="w-4 h-4" />
                        Test Connection
                      </button>
                      <button
                        onClick={generatePreview}
                        className="btn btn-secondary flex items-center gap-2 flex-1"
                        disabled={!labelTemplate || !selectedLabelSize}
                      >
                        👁️ Preview
                      </button>
                    </div>

                    <button
                      onClick={printTestLabel}
                      className="btn btn-primary w-full flex items-center gap-2 justify-center"
                      disabled={!selectedPrinter || !labelTemplate || !selectedLabelSize}
                    >
                      <Printer className="w-4 h-4" />
                      Print Test Label
                    </button>
                  </div>
                </div>

                {/* Preview Panel */}
                <div className="space-y-4">
                  <h4 className="font-medium text-primary">Label Preview</h4>
                  <div className="bg-background-secondary rounded-lg p-4 flex items-center justify-center min-h-48">
                    {previewUrl ? (
                      <div className="text-center">
                        <img
                          src={previewUrl}
                          alt="Label Preview"
                          className="max-w-full max-h-40 border border-border rounded"
                        />
                        <p className="text-sm text-secondary mt-2">Label Preview</p>
                      </div>
                    ) : (
                      <div className="text-center text-muted">
                        <Printer className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>Click "Preview" to see how your label will look</p>
                      </div>
                    )}
                  </div>

                  {/* Quick Template Options */}
                  <div className="bg-background-secondary rounded-lg p-4">
                    <h5 className="font-medium text-primary mb-3">Quick Template Examples</h5>
                    <div className="grid grid-cols-1 gap-2">
                      {[
                        { name: "Part Name Only", template: "{part_name}" },
                        { name: "Part Number", template: "{part_number}" },
                        { name: "Name + Number", template: "{part_name}\n{part_number}" },
                        { name: "Name + QR", template: "{part_name}\n{qr=part_number}" },
                        { name: "Location Label", template: "{location}\n{part_name}" },
                        { name: "Full Info", template: "{part_name}\n{part_number}\nLoc: {location}" }
                      ].map((example) => (
                        <button
                          key={example.name}
                          onClick={() => setLabelTemplate(example.template)}
                          className="btn btn-secondary text-xs py-1 text-left"
                        >
                          <div className="font-medium">{example.name}</div>
                          <div className="text-muted font-mono text-xs">{example.template}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Printer className="w-12 h-12 text-muted mx-auto mb-2" />
                <h3 className="text-lg font-semibold text-primary mb-2">
                  No Printers Registered
                </h3>
                <p className="text-secondary mb-4">
                  Add your Brother QL label printer to start printing labels.
                </p>
                <button
                  onClick={() => {
                    setShowAddPrinter(true)
                    loadSupportedDrivers()
                  }}
                  className="btn btn-primary"
                >
                  Add Your First Printer
                </button>
              </div>
            )}

            {/* Add Printer Modal */}
            {showAddPrinter && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-background-primary rounded-lg p-6 w-full max-w-md mx-4"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-primary">Add New Printer</h4>
                    <button
                      onClick={() => setShowAddPrinter(false)}
                      className="text-secondary hover:text-primary"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Printer ID *
                        </label>
                        <input
                          type="text"
                          className="input w-full"
                          value={newPrinter.printer_id}
                          onChange={(e) => setNewPrinter({...newPrinter, printer_id: e.target.value})}
                          placeholder="e.g., brother_ql_main"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Display Name *
                        </label>
                        <input
                          type="text"
                          className="input w-full"
                          value={newPrinter.name}
                          onChange={(e) => setNewPrinter({...newPrinter, name: e.target.value})}
                          placeholder="e.g., Main Label Printer"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Driver Type
                        </label>
                        <select
                          className="input w-full"
                          value={newPrinter.driver_type}
                          onChange={(e) => setNewPrinter({...newPrinter, driver_type: e.target.value})}
                        >
                          <option value="brother_ql">Brother QL</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Model
                        </label>
                        <select
                          className="input w-full"
                          value={newPrinter.model}
                          onChange={(e) => setNewPrinter({...newPrinter, model: e.target.value})}
                        >
                          <option value="QL-800">QL-800</option>
                          <option value="QL-810W">QL-810W</option>
                          <option value="QL-820NWB">QL-820NWB</option>
                          <option value="QL-1100">QL-1100</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Backend
                        </label>
                        <select
                          className="input w-full"
                          value={newPrinter.backend}
                          onChange={(e) => setNewPrinter({...newPrinter, backend: e.target.value})}
                        >
                          <option value="network">Network (TCP/IP)</option>
                          <option value="usb">USB</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Connection *
                        </label>
                        <input
                          type="text"
                          className="input w-full"
                          value={newPrinter.identifier}
                          onChange={(e) => setNewPrinter({...newPrinter, identifier: e.target.value})}
                          placeholder={newPrinter.backend === 'network' ? 'tcp://192.168.1.71:9100' : 'usb://0x04f9:0x209b'}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          DPI
                        </label>
                        <select
                          className="input w-full"
                          value={newPrinter.dpi}
                          onChange={(e) => setNewPrinter({...newPrinter, dpi: parseInt(e.target.value)})}
                        >
                          <option value={300}>300 DPI</option>
                          <option value={600}>600 DPI</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-primary mb-2">
                          Scaling Factor
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.5"
                          max="2.0"
                          className="input w-full"
                          value={newPrinter.scaling_factor}
                          onChange={(e) => setNewPrinter({...newPrinter, scaling_factor: parseFloat(e.target.value)})}
                        />
                      </div>
                    </div>

                    {/* Discovery Section */}
                    <div className="bg-background-secondary rounded-lg p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-primary">Network Discovery</span>
                        <button
                          onClick={discoverPrinters}
                          disabled={loading}
                          className="btn btn-secondary text-xs py-1 px-2"
                        >
                          {loading ? 'Scanning...' : 'Discover'}
                        </button>
                      </div>
                      
                      {discoveredPrinters.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-xs text-secondary">Found printers:</span>
                          {discoveredPrinters.map((printer, index) => (
                            <button
                              key={index}
                              onClick={() => setNewPrinter({...newPrinter, identifier: printer.identifier})}
                              className="block w-full text-left text-xs p-2 bg-background-primary rounded hover:bg-primary/10 text-primary"
                            >
                              {printer.identifier} ({printer.ip})
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Test Connection */}
                    <div className="bg-background-secondary rounded-lg p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-primary">Test Setup</span>
                        <button
                          onClick={testPrinterSetup}
                          disabled={testingSetup || !newPrinter.identifier}
                          className="btn btn-secondary text-xs py-1 px-2"
                        >
                          {testingSetup ? 'Testing...' : 'Test Connection'}
                        </button>
                      </div>
                      
                      {testResult && (
                        <div className={`text-xs p-2 rounded ${testResult.success ? 'bg-success/20 text-success' : 'bg-error/20 text-error'}`}>
                          <strong>{testResult.success ? '✅ Success' : '❌ Failed'}:</strong> {testResult.message}
                          {testResult.response_time_ms && (
                            <span className="ml-2">({testResult.response_time_ms}ms)</span>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="bg-background-secondary rounded-lg p-3 text-sm text-secondary">
                      <strong>Connection Examples:</strong>
                      <br />• Network: tcp://192.168.1.71:9100
                      <br />• USB: usb://0x04f9:0x209b
                      <br />• Scaling Factor 1.1 is recommended for 39mm labels
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={() => setShowAddPrinter(false)}
                      className="btn btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleAddPrinter}
                      className="btn btn-primary flex-1"
                      disabled={!newPrinter.printer_id || !newPrinter.name || !newPrinter.identifier}
                    >
                      Add Printer
                    </button>
                  </div>
                </motion.div>
              </div>
            )}
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
                      ? 'border-primary bg-primary/10 text-primary' 
                      : 'border-border hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <Sun className="w-8 h-8" />
                  <div className="text-center">
                    <div className="font-medium">Light</div>
                    <div className="text-sm opacity-75">Bright interface</div>
                  </div>
                </button>
                
                <button
                  onClick={() => !isDarkMode && toggleDarkMode()}
                  className={`flex flex-col items-center gap-3 p-4 rounded-lg border transition-all ${
                    isDarkMode 
                      ? 'border-primary bg-primary/10 text-primary' 
                      : 'border-border hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <Moon className="w-8 h-8" />
                  <div className="text-center">
                    <div className="font-medium">Dark</div>
                    <div className="text-sm opacity-75">Dark interface</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Theme Selection */}
            <div className="space-y-4">
              <h4 className="text-md font-medium text-primary">Color Theme</h4>
              <ThemeSelector 
                currentTheme={currentTheme} 
                onThemeChange={setTheme}
              />
            </div>

            {/* Additional Appearance Options */}
            <div className="space-y-4">
              <h4 className="text-md font-medium text-primary">Interface Options</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Animations</span>
                    <p className="text-sm text-secondary">Enable smooth transitions</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Compact Mode</span>
                    <p className="text-sm text-secondary">Reduce spacing and padding</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={isCompactMode}
                      onChange={toggleCompactMode}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary dark:bg-gray-600"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">Show Tooltips</span>
                    <p className="text-sm text-secondary">Display helpful hints</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-primary font-medium">High Contrast</span>
                    <p className="text-sm text-secondary">Improve text readability</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" />
                    <div className="w-11 h-6 bg-background-tertiary peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'suppliers' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-primary mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Supplier Configuration
            </h3>
            <div className="text-sm text-secondary mb-4">
              Manage supplier API configurations, credentials, and enrichment capabilities
            </div>
            <SupplierConfigPage />
          </div>
        )}

        {activeTab === 'security' && (
          <div className="text-center py-8">
            <Shield className="w-12 h-12 text-muted mx-auto mb-2" />
            <h3 className="text-lg font-semibold text-primary mb-2">
              Security Settings Coming Soon
            </h3>
            <p className="text-secondary">
              This section is being developed.
            </p>
          </div>
        )}
      </motion.div>

    </div>
  )
}

export default SettingsPage