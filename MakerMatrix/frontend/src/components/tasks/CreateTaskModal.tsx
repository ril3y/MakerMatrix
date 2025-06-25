import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X, Play, Settings, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { tasksService } from '@/services/tasks.service'

interface CreateTaskModalProps {
  isOpen: boolean
  onClose: () => void
  onTaskCreated: () => void
}

interface TaskTemplate {
  id: string
  name: string
  description: string
  task_type: string
  default_priority: string
  requires_part_id?: boolean
  requires_custom_data?: boolean
  example_input?: any
}

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({ isOpen, onClose, onTaskCreated }) => {
  const [selectedTemplate, setSelectedTemplate] = useState<TaskTemplate | null>(null)
  const [customTaskData, setCustomTaskData] = useState({
    name: '',
    description: '',
    task_type: 'custom',
    priority: 'normal' as 'low' | 'normal' | 'high' | 'urgent',
    input_data: {},
    max_retries: 3,
    timeout_seconds: 300,
    related_entity_type: '',
    related_entity_id: ''
  })
  const [templates, setTemplates] = useState<TaskTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [jsonInputData, setJsonInputData] = useState('')

  // Define available task templates
  const taskTemplates: TaskTemplate[] = [
    {
      id: 'part_enrichment',
      name: 'Part Enrichment',
      description: 'Enrich part data from supplier APIs',
      task_type: 'part_enrichment',
      default_priority: 'normal',
      requires_part_id: true,
      example_input: {
        part_id: '',
        supplier: 'LCSC',
        capabilities: ['fetch_datasheet', 'fetch_image'],
        force_refresh: false
      }
    },
    {
      id: 'datasheet_fetch',
      name: 'Datasheet Fetch',
      description: 'Fetch datasheet for a specific part',
      task_type: 'datasheet_fetch',
      default_priority: 'normal',
      requires_part_id: true,
      example_input: {
        part_id: '',
        supplier: 'LCSC'
      }
    },
    {
      id: 'image_fetch',
      name: 'Image Fetch',
      description: 'Fetch images for a specific part',
      task_type: 'image_fetch',
      default_priority: 'normal',
      requires_part_id: true,
      example_input: {
        part_id: '',
        supplier: 'LCSC'
      }
    },
    {
      id: 'bulk_enrichment',
      name: 'Bulk Enrichment',
      description: 'Enrich multiple parts at once',
      task_type: 'bulk_enrichment',
      default_priority: 'normal',
      requires_custom_data: true,
      example_input: {
        part_ids: [],
        supplier: 'LCSC',
        capabilities: ['fetch_datasheet', 'fetch_image'],
        batch_size: 10
      }
    },
    {
      id: 'price_update',
      name: 'Price Update',
      description: 'Update pricing information for parts',
      task_type: 'price_update',
      default_priority: 'low',
      example_input: {
        supplier: 'LCSC',
        update_all: true
      }
    },
    {
      id: 'database_cleanup',
      name: 'Database Cleanup',
      description: 'Clean up and optimize database',
      task_type: 'database_cleanup',
      default_priority: 'low',
      example_input: {
        vacuum: true,
        analyze: true,
        cleanup_old_tasks: true
      }
    }
  ]

  useEffect(() => {
    setTemplates(taskTemplates)
  }, [])

  useEffect(() => {
    if (selectedTemplate) {
      setCustomTaskData(prev => ({
        ...prev,
        name: selectedTemplate.name,
        description: selectedTemplate.description,
        task_type: selectedTemplate.task_type,
        priority: selectedTemplate.default_priority as any
      }))
      setJsonInputData(JSON.stringify(selectedTemplate.example_input || {}, null, 2))
    }
  }, [selectedTemplate])

  const handleSubmit = async () => {
    try {
      setLoading(true)

      // Validate required fields
      if (!customTaskData.name.trim()) {
        toast.error('Task name is required')
        return
      }

      // Parse JSON input data
      let inputData = {}
      if (jsonInputData.trim()) {
        try {
          inputData = JSON.parse(jsonInputData)
        } catch (error) {
          toast.error('Invalid JSON in input data')
          return
        }
      }

      // Create task
      const taskRequest = {
        task_type: customTaskData.task_type,
        name: customTaskData.name,
        description: customTaskData.description,
        priority: customTaskData.priority,
        input_data: inputData,
        max_retries: customTaskData.max_retries,
        timeout_seconds: customTaskData.timeout_seconds,
        related_entity_type: customTaskData.related_entity_type || undefined,
        related_entity_id: customTaskData.related_entity_id || undefined
      }

      await tasksService.createTask(taskRequest)
      toast.success('✅ Task created successfully!')
      onTaskCreated()
      onClose()
      
      // Reset form
      setSelectedTemplate(null)
      setCustomTaskData({
        name: '',
        description: '',
        task_type: 'custom',
        priority: 'normal',
        input_data: {},
        max_retries: 3,
        timeout_seconds: 300,
        related_entity_type: '',
        related_entity_id: ''
      })
      setJsonInputData('')
      
    } catch (error: any) {
      console.error('Failed to create task:', error)
      toast.error(`❌ Failed to create task: ${error?.response?.data?.detail || error.message}`)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-theme-elevated border border-theme-primary rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-theme-primary">
          <div>
            <h2 className="text-xl font-semibold text-primary">Create Custom Task</h2>
            <p className="text-sm text-secondary mt-1">Create a new background task</p>
          </div>
          <button
            onClick={onClose}
            className="text-secondary hover:text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Template Selection */}
          <div className="mb-6 p-4 bg-background-secondary rounded-lg">
            <label className="block text-sm font-medium text-primary mb-3">
              Choose a Template (Optional)
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {templates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setSelectedTemplate(template)}
                  className={`p-3 text-left border rounded-lg transition-colors ${
                    selectedTemplate?.id === template.id
                      ? 'border-accent bg-accent/10'
                      : 'border-border hover:border-accent/50'
                  }`}
                >
                  <div className="font-medium text-primary text-sm">{template.name}</div>
                  <div className="text-xs text-secondary mt-1">{template.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Task Configuration */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Task Name *
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="My Custom Task"
                  value={customTaskData.name}
                  onChange={(e) => setCustomTaskData(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Priority
                </label>
                <select
                  className="input w-full"
                  value={customTaskData.priority}
                  onChange={(e) => setCustomTaskData(prev => ({ ...prev, priority: e.target.value as any }))}
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Description
              </label>
              <textarea
                className="input w-full h-20 resize-none"
                placeholder="Describe what this task will do..."
                value={customTaskData.description}
                onChange={(e) => setCustomTaskData(prev => ({ ...prev, description: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Task Type
                </label>
                <input
                  type="text"
                  className="input w-full"
                  placeholder="custom"
                  value={customTaskData.task_type}
                  onChange={(e) => setCustomTaskData(prev => ({ ...prev, task_type: e.target.value }))}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-primary mb-2">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  className="input w-full"
                  min="30"
                  max="3600"
                  value={customTaskData.timeout_seconds}
                  onChange={(e) => setCustomTaskData(prev => ({ ...prev, timeout_seconds: parseInt(e.target.value) || 300 }))}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-primary mb-2">
                Input Data (JSON)
              </label>
              <textarea
                className="input w-full h-32 font-mono text-sm resize-none"
                placeholder='{"key": "value"}'
                value={jsonInputData}
                onChange={(e) => setJsonInputData(e.target.value)}
              />
              <p className="text-xs text-secondary mt-1">
                Provide task-specific configuration as JSON
              </p>
            </div>

            {selectedTemplate?.requires_part_id && (
              <div className="bg-accent/10 border border-accent/20 rounded-lg p-3">
                <div className="flex items-center gap-2 text-accent mb-1">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Part ID Required</span>
                </div>
                <p className="text-xs text-secondary">
                  This task type requires a valid part_id in the input data.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-theme-primary">
          <button
            onClick={onClose}
            className="btn btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="btn btn-primary"
            disabled={loading || !customTaskData.name.trim()}
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Create Task
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default CreateTaskModal