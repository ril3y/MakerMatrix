import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, FileText, Image, DollarSign, Package, Info, RefreshCw, CheckCircle, AlertCircle, Download } from 'lucide-react'
import { tasksService, Task } from '@/services/tasks.service'

interface CSVEnrichmentProgressModalProps {
  isOpen: boolean
  onClose: () => void
  enrichmentTaskId?: string
  importedPartsCount: number
  fileName: string
}

interface EnrichmentCapability {
  name: string
  icon: any
  label: string
  success: number
  failed: number
  total: number
}

const CSVEnrichmentProgressModal = ({ 
  isOpen, 
  onClose, 
  enrichmentTaskId, 
  importedPartsCount,
  fileName 
}: CSVEnrichmentProgressModalProps) => {
  console.log('CSVEnrichmentProgressModal props:', { isOpen, enrichmentTaskId, importedPartsCount, fileName })
  const [currentTask, setCurrentTask] = useState<Task | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [capabilities, setCapabilities] = useState<EnrichmentCapability[]>([])
  const [isCompleted, setIsCompleted] = useState(false)
  const [totalPartsEnriched, setTotalPartsEnriched] = useState(0)
  const [successfulEnrichments, setSuccessfulEnrichments] = useState(0)
  const [failedEnrichments, setFailedEnrichments] = useState(0)

  // Capability icons mapping
  const capabilityIcons = {
    fetch_datasheet: { icon: FileText, label: 'Datasheets' },
    fetch_image: { icon: Image, label: 'Images' },
    fetch_pricing: { icon: DollarSign, label: 'Pricing' },
    fetch_stock: { icon: Package, label: 'Stock Info' },
    fetch_specifications: { icon: RefreshCw, label: 'Specifications' },
    enrich_basic_info: { icon: Info, label: 'Basic Info' }
  }

  useEffect(() => {
    if (!enrichmentTaskId || !isOpen) return

    let stopPolling: (() => void) | null = null

    const startPolling = async () => {
      try {
        stopPolling = await tasksService.pollTaskProgress(
          enrichmentTaskId,
          (task: Task) => {
            setCurrentTask(task)
            setTaskProgress(task.progress_percentage || 0)
            setCurrentStep(task.current_step || 'Processing...')

            // Parse enrichment results if available
            if (task.result_data) {
              try {
                const results = typeof task.result_data === 'string' 
                  ? JSON.parse(task.result_data) 
                  : task.result_data

                if (results.enrichment_summary) {
                  const summary = results.enrichment_summary
                  setTotalPartsEnriched(summary.total_parts_processed || 0)
                  setSuccessfulEnrichments(summary.successful_enrichments || 0)
                  setFailedEnrichments(summary.failed_enrichments || 0)

                  // Update capability stats
                  if (summary.capability_results) {
                    const capabilityList: EnrichmentCapability[] = Object.entries(summary.capability_results).map(([capName, stats]: [string, any]) => ({
                      name: capName,
                      icon: capabilityIcons[capName as keyof typeof capabilityIcons]?.icon || Info,
                      label: capabilityIcons[capName as keyof typeof capabilityIcons]?.label || capName,
                      success: stats.success || 0,
                      failed: stats.failed || 0,
                      total: stats.total || 0
                    }))
                    setCapabilities(capabilityList)
                  }
                }
              } catch (e) {
                console.warn('Failed to parse enrichment results:', e)
              }
            }

            if (['completed', 'failed', 'cancelled'].includes(task.status)) {
              setIsCompleted(true)
            }
          },
          1000 // Poll every second
        )
      } catch (error) {
        console.error('Failed to start task polling:', error)
      }
    }

    startPolling()

    return () => {
      if (stopPolling) {
        stopPolling()
      }
    }
  }, [enrichmentTaskId, isOpen])

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-background border border-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        >
          <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-primary">CSV Import Enrichment</h3>
                <p className="text-sm text-secondary mt-1">
                  Enriching {importedPartsCount} parts from {fileName}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-background-secondary rounded-lg transition-colors"
                disabled={!isCompleted}
                title={isCompleted ? "Close" : "Enrichment in progress..."}
              >
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>

            {/* Progress Overview */}
            {!isCompleted && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="inline-flex items-center gap-3 p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                    <div>
                      <div className="font-medium text-primary">Enriching Part Data</div>
                      <div className="text-sm text-secondary">{currentStep}</div>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-secondary">Overall Progress</span>
                    <span className="text-primary">{taskProgress}%</span>
                  </div>
                  <div className="w-full bg-background-secondary rounded-full h-2">
                    <motion.div
                      className="bg-blue-500 h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${taskProgress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>

                {/* Current Stats */}
                {totalPartsEnriched > 0 && (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-background-secondary rounded-lg">
                    <div className="text-center">
                      <div className="text-lg font-semibold text-primary">{totalPartsEnriched}</div>
                      <div className="text-xs text-secondary">Parts Processed</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-success">{successfulEnrichments}</div>
                      <div className="text-xs text-secondary">Successful</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-semibold text-error">{failedEnrichments}</div>
                      <div className="text-xs text-secondary">Failed</div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Completion Summary */}
            {isCompleted && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="inline-flex items-center gap-3 p-4 bg-success/10 rounded-lg border border-success/20">
                    <CheckCircle className="w-6 h-6 text-success" />
                    <div>
                      <div className="font-medium text-primary">Enrichment Complete</div>
                      <div className="text-sm text-secondary">
                        {successfulEnrichments} of {totalPartsEnriched} parts enriched successfully
                      </div>
                    </div>
                  </div>
                </div>

                {/* Final Stats */}
                <div className="grid grid-cols-3 gap-4 p-4 bg-background-secondary rounded-lg">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">{totalPartsEnriched}</div>
                    <div className="text-sm text-secondary">Total Processed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-success">{successfulEnrichments}</div>
                    <div className="text-sm text-secondary">Successful</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-error">{failedEnrichments}</div>
                    <div className="text-sm text-secondary">Failed</div>
                  </div>
                </div>

                {/* Capability Results */}
                {capabilities.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-primary">Enrichment Results by Capability</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {capabilities.map((capability) => {
                        const IconComponent = capability.icon
                        const successRate = capability.total > 0 ? (capability.success / capability.total * 100) : 0
                        
                        return (
                          <div
                            key={capability.name}
                            className="p-4 bg-background-secondary rounded-lg border border-border"
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <div className="p-2 bg-blue-500/20 rounded-lg">
                                <IconComponent className="w-4 h-4 text-blue-400" />
                              </div>
                              <div className="flex-1">
                                <div className="font-medium text-primary">{capability.label}</div>
                                <div className="text-sm text-secondary">
                                  {capability.success}/{capability.total} ({successRate.toFixed(0)}%)
                                </div>
                              </div>
                            </div>
                            <div className="w-full bg-background-tertiary rounded-full h-1.5">
                              <div
                                className="bg-success h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${successRate}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Task Details */}
                {currentTask && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-primary">Task Details</h4>
                    <div className="p-3 bg-background-secondary rounded-lg text-sm">
                      <div className="flex justify-between">
                        <span className="text-secondary">Status:</span>
                        <span className={`font-medium ${
                          currentTask.status === 'completed' ? 'text-success' : 
                          currentTask.status === 'failed' ? 'text-error' : 'text-primary'
                        }`}>
                          {currentTask.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-secondary">Duration:</span>
                        <span className="text-primary">
                          {currentTask.started_at && currentTask.completed_at
                            ? `${Math.round((new Date(currentTask.completed_at).getTime() - new Date(currentTask.started_at).getTime()) / 1000)}s`
                            : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Close Button */}
            {isCompleted && (
              <div className="flex justify-end pt-4 border-t border-border">
                <button 
                  onClick={onClose} 
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default CSVEnrichmentProgressModal