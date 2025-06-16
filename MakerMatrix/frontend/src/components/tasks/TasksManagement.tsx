import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity, Play, Square, RotateCcw, Plus, Filter, 
  Clock, CheckCircle, XCircle, AlertCircle, Pause,
  Eye, EyeOff, Monitor, Trash2, RefreshCw, Zap
} from 'lucide-react'
import toast from 'react-hot-toast'
import { tasksService } from '@/services/tasks.service'
import { partsService } from '@/services/parts.service'

interface Task {
  id: string
  task_type: string
  name: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'normal' | 'high' | 'urgent'
  progress_percentage: number
  current_step?: string
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  result_data?: any
  related_entity_type?: string
  related_entity_id?: string
}

interface WorkerStatus {
  is_running: boolean
  running_tasks_count: number
  running_task_ids: string[]
  registered_handlers: number
}

interface TaskStats {
  total_tasks: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  running_tasks: number
  failed_tasks: number
  completed_today: number
}

const TasksManagement: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([])
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null)
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showTaskConsole, setShowTaskConsole] = useState(false)
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  
  // Console/monitoring
  const [consoleVisible, setConsoleVisible] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const refreshInterval = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    loadTasks()
    loadWorkerStatus()
    loadTaskStats()
    
    if (autoRefresh) {
      refreshInterval.current = setInterval(() => {
        loadTasks()
        loadWorkerStatus()
        loadTaskStats()
      }, 2000) // Refresh every 2 seconds
    }
    
    return () => {
      if (refreshInterval.current) {
        clearInterval(refreshInterval.current)
      }
    }
  }, [autoRefresh])

  useEffect(() => {
    // Apply filters
    let filtered = tasks
    
    if (statusFilter !== 'all') {
      filtered = filtered.filter(task => task.status === statusFilter)
    }
    
    if (typeFilter !== 'all') {
      filtered = filtered.filter(task => task.task_type === typeFilter)
    }
    
    if (priorityFilter !== 'all') {
      filtered = filtered.filter(task => task.priority === priorityFilter)
    }
    
    setFilteredTasks(filtered)
  }, [tasks, statusFilter, typeFilter, priorityFilter])

  const loadTasks = async () => {
    try {
      const response = await tasksService.getTasks()
      setTasks(response.data || [])
    } catch (error) {
      console.error('Failed to load tasks:', error)
      if (!tasks.length) { // Only show error if we don't have cached data
        toast.error('Failed to load tasks')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadWorkerStatus = async () => {
    try {
      const status = await tasksService.getWorkerStatus()
      setWorkerStatus(status.data)
    } catch (error) {
      console.error('Failed to load worker status:', error)
    }
  }

  const loadTaskStats = async () => {
    try {
      const stats = await tasksService.getTaskStats()
      setTaskStats(stats.data)
    } catch (error) {
      console.error('Failed to load task stats:', error)
    }
  }

  const startWorker = async () => {
    try {
      await tasksService.startWorker()
      toast.success('Task worker started')
      loadWorkerStatus()
    } catch (error) {
      toast.error('Failed to start worker')
    }
  }

  const stopWorker = async () => {
    try {
      await tasksService.stopWorker()
      toast.success('Task worker stopped')
      loadWorkerStatus()
    } catch (error) {
      toast.error('Failed to stop worker')
    }
  }

  const cancelTask = async (taskId: string) => {
    try {
      await tasksService.cancelTask(taskId)
      toast.success('Task cancelled')
      loadTasks()
    } catch (error) {
      toast.error('Failed to cancel task')
    }
  }

  const retryTask = async (taskId: string) => {
    try {
      await tasksService.retryTask(taskId)
      toast.success('Task retry scheduled')
      loadTasks()
    } catch (error) {
      toast.error('Failed to retry task')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock className="w-4 h-4 text-yellow-500" />
      case 'running': return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-500" />
      case 'cancelled': return <Pause className="w-4 h-4 text-muted" />
      default: return <AlertCircle className="w-4 h-4 text-muted" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-error bg-error/20'
      case 'high': return 'text-warning bg-warning/20'
      case 'normal': return 'text-info bg-info/20'
      case 'low': return 'text-muted bg-background-tertiary'
      default: return 'text-muted bg-background-tertiary'
    }
  }

  const formatTaskType = (type: string) => {
    return type.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ')
  }

  const formatDuration = (startTime?: string, endTime?: string) => {
    if (!startTime) return 'Not started'
    
    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()
    const duration = Math.round((end.getTime() - start.getTime()) / 1000)
    
    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.round(duration / 60)}m`
    return `${Math.round(duration / 3600)}h`
  }

  const createQuickTask = async (taskType: string) => {
    try {
      let taskData = {}
      
      switch (taskType) {
        case 'price-update':
          taskData = { update_all: true }
          break
        case 'database-cleanup':
          taskData = { cleanup_type: 'full' }
          break
        case 'csv-enrichment':
          taskData = { enrichment_queue: [] }
          break
        case 'bulk-enrichment':
          try {
            toast.loading('Fetching parts for enrichment...', { id: 'bulk-enrichment-loading' })
            const allParts = await partsService.getAll()
            const partIds = allParts.map(part => part.id).filter(id => id) // Filter out any null/undefined IDs
            
            toast.dismiss('bulk-enrichment-loading')
            
            if (partIds.length === 0) {
              toast.error('No parts found to enrich')
              return
            }
            
            taskData = { 
              part_ids: partIds, 
              batch_size: 10,
              capabilities: ['fetch_pricing', 'fetch_datasheet', 'fetch_specifications'],
              force_refresh: false
            }
            toast.success(`Found ${partIds.length} parts for enrichment`)
          } catch (error) {
            toast.dismiss('bulk-enrichment-loading')
            toast.error(`Failed to fetch parts: ${error.message}`)
            return
          }
          break
      }
      
      console.log('Creating task:', taskType, taskData)
      const response = await tasksService.createQuickTask(taskType, taskData)
      console.log('Task creation response:', response)
      toast.success('Task created successfully')
      
      // Reload tasks and worker status
      await loadTasks()
      await loadWorkerStatus()
      await loadTaskStats()
    } catch (error) {
      console.error('Failed to create task:', error)
      toast.error(`Failed to create task: ${error.response?.data?.detail || error.message}`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header with Worker Status */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Background Tasks
            {workerStatus && (
              <span className={`text-xs px-2 py-1 rounded-full ${
                workerStatus.is_running 
                  ? 'bg-success/20 text-success' 
                  : 'bg-error/20 text-error'
              }`}>
                {workerStatus.is_running ? 'Worker Running' : 'Worker Stopped'}
              </span>
            )}
          </h3>
          <p className="text-secondary text-sm">
            Manage and monitor background tasks and processes
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`btn btn-sm ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={() => setConsoleVisible(!consoleVisible)}
            className="btn btn-secondary btn-sm"
          >
            {consoleVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            Console
          </button>
          
          {workerStatus?.is_running ? (
            <button onClick={stopWorker} className="btn btn-destructive btn-sm">
              <Square className="w-4 h-4" />
              Stop Worker
            </button>
          ) : (
            <button onClick={startWorker} className="btn btn-primary btn-sm">
              <Play className="w-4 h-4" />
              Start Worker
            </button>
          )}
        </div>
      </div>

      {/* Task Stats */}
      {taskStats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-primary">{taskStats.total_tasks}</div>
            <div className="text-sm text-secondary">Total Tasks</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-info">{taskStats.running_tasks}</div>
            <div className="text-sm text-secondary">Running</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-success">{taskStats.completed_today}</div>
            <div className="text-sm text-secondary">Completed Today</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-error">{taskStats.failed_tasks}</div>
            <div className="text-sm text-secondary">Failed</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-warning">
              {taskStats.by_status?.pending || 0}
            </div>
            <div className="text-sm text-secondary">Pending</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-muted">
              {workerStatus?.registered_handlers || 0}
            </div>
            <div className="text-sm text-secondary">Handlers</div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="card p-4">
        <h4 className="font-medium text-primary mb-3">Quick Actions</h4>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => createQuickTask('price-update')}
            className="btn btn-secondary btn-sm"
          >
            <Zap className="w-4 h-4" />
            Update Prices
          </button>
          <button
            onClick={() => createQuickTask('bulk-enrichment')}
            className="btn btn-secondary btn-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Enrich All Parts
          </button>
          <button
            onClick={() => createQuickTask('database-cleanup')}
            className="btn btn-secondary btn-sm"
          >
            <Trash2 className="w-4 h-4" />
            Clean Database
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary btn-sm"
          >
            <Plus className="w-4 h-4" />
            Create Custom Task
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-secondary" />
            <span className="text-sm text-primary font-medium">Filters:</span>
          </div>
          
          <select
            className="input input-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          
          <select
            className="input input-sm"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="csv_enrichment">CSV Enrichment</option>
            <option value="bulk_enrichment">Bulk Enrichment</option>
            <option value="part_enrichment">Part Enrichment</option>
            <option value="price_update">Price Update</option>
            <option value="database_cleanup">Database Cleanup</option>
            <option value="file_download">File Download</option>
            <option value="data_sync">Data Sync</option>
          </select>
          
          <select
            className="input input-sm"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
          
          <button
            onClick={() => {
              setStatusFilter('all')
              setTypeFilter('all')
              setPriorityFilter('all')
            }}
            className="btn btn-secondary btn-sm"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Tasks List */}
      <div className="card">
        <div className="p-4 border-b border-border">
          <h4 className="font-medium text-primary">
            Tasks ({filteredTasks.length})
          </h4>
        </div>
        
        <div className="divide-y divide-border">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
              <p className="text-secondary mt-2">Loading tasks...</p>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="p-8 text-center">
              <Activity className="w-8 h-8 mx-auto text-muted mb-2" />
              <p className="text-secondary">No tasks found</p>
            </div>
          ) : (
            filteredTasks.map((task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-4 hover:bg-background-secondary transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(task.status)}
                      <h5 className="font-medium text-primary truncate">
                        {task.name}
                      </h5>
                      <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                      <span className="text-xs text-secondary">
                        {formatTaskType(task.task_type)}
                      </span>
                    </div>
                    
                    {task.description && (
                      <p className="text-sm text-secondary truncate mb-2">
                        {task.description}
                      </p>
                    )}
                    
                    {task.current_step && (
                      <p className="text-sm text-primary mb-2">
                        {task.current_step}
                      </p>
                    )}
                    
                    {task.status === 'running' && (
                      <div className="w-full bg-background-tertiary rounded-full h-2 mb-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${task.progress_percentage}%` }}
                        />
                      </div>
                    )}
                    
                    <div className="flex items-center gap-4 text-xs text-secondary">
                      <span>Created: {new Date(task.created_at).toLocaleString()}</span>
                      {task.started_at && (
                        <span>Duration: {formatDuration(task.started_at, task.completed_at)}</span>
                      )}
                      {task.progress_percentage > 0 && (
                        <span>{task.progress_percentage}% complete</span>
                      )}
                    </div>
                    
                    {task.error_message && (
                      <div className="mt-2 p-2 bg-error/10 border border-error/20 rounded text-sm text-error">
                        Error: {task.error_message}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="btn btn-secondary btn-sm"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    
                    {task.status === 'running' && (
                      <button
                        onClick={() => cancelTask(task.id)}
                        className="btn btn-destructive btn-sm"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                    )}
                    
                    {task.status === 'failed' && (
                      <button
                        onClick={() => retryTask(task.id)}
                        className="btn btn-primary btn-sm"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Task Console */}
      <AnimatePresence>
        {consoleVisible && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card"
          >
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h4 className="font-medium text-primary flex items-center gap-2">
                <Monitor className="w-4 h-4" />
                Task Console
              </h4>
              <button
                onClick={() => setConsoleVisible(false)}
                className="btn btn-secondary btn-sm"
              >
                <XCircle className="w-4 h-4" />
              </button>
            </div>
            
            <div className="p-4 bg-background-primary dark:bg-black text-success font-mono text-sm min-h-[200px] max-h-[300px] overflow-y-auto custom-scrollbar">
              {tasks.filter(t => t.status === 'running').map(task => (
                <div key={task.id} className="mb-2">
                  <span className="text-info">[{new Date().toLocaleTimeString()}]</span>
                  <span className="text-warning"> {task.name}:</span>
                  <span className="text-success"> {task.current_step || 'Running...'}</span>
                  <span className="text-muted"> ({task.progress_percentage}%)</span>
                </div>
              ))}
              {tasks.filter(t => t.status === 'running').length === 0 && (
                <div className="text-muted">No running tasks to monitor...</div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-background-primary rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-primary">
                  Task Details
                </h3>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="btn btn-secondary btn-sm"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-secondary">Task ID</label>
                  <p className="font-mono text-sm">{selectedTask.id}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-secondary">Type</label>
                  <p>{formatTaskType(selectedTask.task_type)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-secondary">Status</label>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(selectedTask.status)}
                    <span className="capitalize">{selectedTask.status}</span>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-secondary">Priority</label>
                  <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(selectedTask.priority)}`}>
                    {selectedTask.priority}
                  </span>
                </div>
              </div>
              
              {selectedTask.description && (
                <div>
                  <label className="text-sm font-medium text-secondary">Description</label>
                  <p>{selectedTask.description}</p>
                </div>
              )}
              
              {selectedTask.current_step && (
                <div>
                  <label className="text-sm font-medium text-secondary">Current Step</label>
                  <p>{selectedTask.current_step}</p>
                </div>
              )}
              
              {selectedTask.error_message && (
                <div>
                  <label className="text-sm font-medium text-secondary">Error Message</label>
                  <div className="p-3 bg-error/10 border border-error/20 rounded text-error">
                    {selectedTask.error_message}
                  </div>
                </div>
              )}
              
              {selectedTask.result_data && (
                <div>
                  <label className="text-sm font-medium text-secondary">Result Data</label>
                  <pre className="p-3 bg-background-secondary rounded text-sm overflow-x-auto">
                    {JSON.stringify(selectedTask.result_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}

export default TasksManagement