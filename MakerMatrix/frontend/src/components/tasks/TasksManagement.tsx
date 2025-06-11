import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity, Play, Square, RotateCcw, Plus, Filter, 
  Clock, CheckCircle, XCircle, AlertCircle, Pause,
  Eye, EyeOff, Monitor, Trash2, RefreshCw, Zap
} from 'lucide-react'
import toast from 'react-hot-toast'
import { tasksService } from '@/services/tasks.service'

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
      case 'cancelled': return <Pause className="w-4 h-4 text-gray-500" />
      default: return <AlertCircle className="w-4 h-4 text-gray-500" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-100'
      case 'high': return 'text-orange-600 bg-orange-100'
      case 'normal': return 'text-blue-600 bg-blue-100'
      case 'low': return 'text-gray-600 bg-gray-100'
      default: return 'text-gray-600 bg-gray-100'
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
      }
      
      await tasksService.createQuickTask(taskType, taskData)
      toast.success('Task created successfully')
      loadTasks()
    } catch (error) {
      toast.error('Failed to create task')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header with Worker Status */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Background Tasks
            {workerStatus && (
              <span className={`text-xs px-2 py-1 rounded-full ${
                workerStatus.is_running 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {workerStatus.is_running ? 'Worker Running' : 'Worker Stopped'}
              </span>
            )}
          </h3>
          <p className="text-text-secondary text-sm">
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
            <div className="text-sm text-text-secondary">Total Tasks</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{taskStats.running_tasks}</div>
            <div className="text-sm text-text-secondary">Running</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{taskStats.completed_today}</div>
            <div className="text-sm text-text-secondary">Completed Today</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{taskStats.failed_tasks}</div>
            <div className="text-sm text-text-secondary">Failed</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {taskStats.by_status?.pending || 0}
            </div>
            <div className="text-sm text-text-secondary">Pending</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-gray-600">
              {workerStatus?.registered_handlers || 0}
            </div>
            <div className="text-sm text-text-secondary">Handlers</div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="card p-4">
        <h4 className="font-medium text-text-primary mb-3">Quick Actions</h4>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => createQuickTask('price-update')}
            className="btn btn-secondary btn-sm"
          >
            <Zap className="w-4 h-4" />
            Update Prices
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
            <Filter className="w-4 h-4 text-text-secondary" />
            <span className="text-sm text-text-primary font-medium">Filters:</span>
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
          <h4 className="font-medium text-text-primary">
            Tasks ({filteredTasks.length})
          </h4>
        </div>
        
        <div className="divide-y divide-border">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary" />
              <p className="text-text-secondary mt-2">Loading tasks...</p>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="p-8 text-center">
              <Activity className="w-8 h-8 mx-auto text-text-muted mb-2" />
              <p className="text-text-secondary">No tasks found</p>
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
                      <h5 className="font-medium text-text-primary truncate">
                        {task.name}
                      </h5>
                      <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                      <span className="text-xs text-text-secondary">
                        {formatTaskType(task.task_type)}
                      </span>
                    </div>
                    
                    {task.description && (
                      <p className="text-sm text-text-secondary truncate mb-2">
                        {task.description}
                      </p>
                    )}
                    
                    {task.current_step && (
                      <p className="text-sm text-primary mb-2">
                        {task.current_step}
                      </p>
                    )}
                    
                    {task.status === 'running' && (
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-300"
                          style={{ width: `${task.progress_percentage}%` }}
                        />
                      </div>
                    )}
                    
                    <div className="flex items-center gap-4 text-xs text-text-secondary">
                      <span>Created: {new Date(task.created_at).toLocaleString()}</span>
                      {task.started_at && (
                        <span>Duration: {formatDuration(task.started_at, task.completed_at)}</span>
                      )}
                      {task.progress_percentage > 0 && (
                        <span>{task.progress_percentage}% complete</span>
                      )}
                    </div>
                    
                    {task.error_message && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
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
              <h4 className="font-medium text-text-primary flex items-center gap-2">
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
            
            <div className="p-4 bg-gray-900 dark:bg-black text-green-400 font-mono text-sm min-h-[200px] max-h-[300px] overflow-y-auto custom-scrollbar">
              {tasks.filter(t => t.status === 'running').map(task => (
                <div key={task.id} className="mb-2">
                  <span className="text-blue-400">[{new Date().toLocaleTimeString()}]</span>
                  <span className="text-yellow-400"> {task.name}:</span>
                  <span className="text-green-400"> {task.current_step || 'Running...'}</span>
                  <span className="text-gray-400"> ({task.progress_percentage}%)</span>
                </div>
              ))}
              {tasks.filter(t => t.status === 'running').length === 0 && (
                <div className="text-gray-500">No running tasks to monitor...</div>
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
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
          >
            <div className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-text-primary">
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
                  <label className="text-sm font-medium text-text-secondary">Task ID</label>
                  <p className="font-mono text-sm">{selectedTask.id}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary">Type</label>
                  <p>{formatTaskType(selectedTask.task_type)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary">Status</label>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(selectedTask.status)}
                    <span className="capitalize">{selectedTask.status}</span>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary">Priority</label>
                  <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(selectedTask.priority)}`}>
                    {selectedTask.priority}
                  </span>
                </div>
              </div>
              
              {selectedTask.description && (
                <div>
                  <label className="text-sm font-medium text-text-secondary">Description</label>
                  <p>{selectedTask.description}</p>
                </div>
              )}
              
              {selectedTask.current_step && (
                <div>
                  <label className="text-sm font-medium text-text-secondary">Current Step</label>
                  <p>{selectedTask.current_step}</p>
                </div>
              )}
              
              {selectedTask.error_message && (
                <div>
                  <label className="text-sm font-medium text-text-secondary">Error Message</label>
                  <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700">
                    {selectedTask.error_message}
                  </div>
                </div>
              )}
              
              {selectedTask.result_data && (
                <div>
                  <label className="text-sm font-medium text-text-secondary">Result Data</label>
                  <pre className="p-3 bg-gray-100 rounded text-sm overflow-x-auto">
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