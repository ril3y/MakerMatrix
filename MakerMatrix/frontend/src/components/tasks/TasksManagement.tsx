import React, { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  Play,
  Square,
  RotateCcw,
  Filter,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Pause,
  Eye,
  EyeOff,
  Monitor,
  Trash2,
  RefreshCw,
  Zap
} from 'lucide-react'
import { Task } from '@/services/tasks.service'
import { useTasksDashboard } from '@/hooks/useTasksDashboard'

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return <Clock className="w-4 h-4 text-yellow-500" />
    case 'running':
      return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-500" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />
    case 'cancelled':
      return <Pause className="w-4 h-4 text-muted" />
    default:
      return <AlertCircle className="w-4 h-4 text-muted" />
  }
}

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'urgent':
      return 'text-error bg-error/20'
    case 'high':
      return 'text-warning bg-warning/20'
    case 'normal':
      return 'text-info bg-info/20'
    case 'low':
      return 'text-muted bg-background-tertiary'
    default:
      return 'text-muted bg-background-tertiary'
  }
}

const formatTaskType = (type: string) =>
  type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')

const formatDuration = (startTime?: string, endTime?: string) => {
  if (!startTime) return 'Not started'

  const start = new Date(startTime)
  const end = endTime ? new Date(endTime) : new Date()
  const duration = Math.round((end.getTime() - start.getTime()) / 1000)

  if (duration < 60) return `${duration}s`
  if (duration < 3600) return `${Math.round(duration / 60)}m`
  return `${Math.round(duration / 3600)}h`
}

const TasksManagement: React.FC = () => {
  const {
    tasks,
    filteredTasks,
    workerStatus,
    taskStats,
    loading,
    statusFilter,
    setStatusFilter,
    typeFilter,
    setTypeFilter,
    priorityFilter,
    setPriorityFilter,
    resetFilters,
    autoRefresh,
    toggleAutoRefresh,
    consoleMessages,
    supplierConfigStatus,
    startWorker,
    stopWorker,
    cancelTask,
    retryTask,
    deleteTask,
    createQuickTask,
    checkSupplierConfigStatus,
    isWebSocketConnected,
    reconnectWebSocket
  } = useTasksDashboard()

  const [consoleVisible, setConsoleVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  const runningTasks = useMemo(
    () => tasks.filter(task => task.status === 'running'),
    [tasks]
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Activity className="w-6 h-6" />
          Background Tasks
        </h1>
        <p className="text-secondary mt-1">
          Monitor and manage background tasks and processes
        </p>
      </div>

      {/* Worker Status and Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {workerStatus && (
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                workerStatus.is_running ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
              }`}
            >
              {workerStatus.is_running ? 'Worker Running' : 'Worker Stopped'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isWebSocketConnected ? 'bg-success' : 'bg-error'
              }`}
            />
            <span className="text-xs text-secondary">
              {isWebSocketConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
            </span>
          </div>

          <button
            onClick={toggleAutoRefresh}
            className={`btn btn-sm ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            <RefreshCw
              className={`w-4 h-4 ${autoRefresh && !isWebSocketConnected ? 'animate-spin' : ''}`}
            />
          </button>

          <button
            onClick={reconnectWebSocket}
            className="btn btn-secondary btn-sm"
            title="Reconnect WebSocket"
          >
            <span className="sr-only">Reconnect WebSocket</span>
            🔄
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

      {/* Supplier Configuration Status Banner */}
      {supplierConfigStatus &&
        (supplierConfigStatus.unconfiguredSuppliers.length > 0 ||
          supplierConfigStatus.partsWithoutSuppliers > 0) && (
          <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-semibold text-warning mb-2">Supplier Configuration Required</h4>
                <div className="space-y-2 text-sm">
                  {supplierConfigStatus.unconfiguredSuppliers.length > 0 && (
                    <p>
                      <span className="font-medium">
                        {supplierConfigStatus.unconfiguredSuppliers.length} supplier(s)
                      </span>{' '}
                      need configuration:{' '}
                      <span className="font-mono text-xs bg-warning/20 px-1 rounded">
                        {supplierConfigStatus.unconfiguredSuppliers.join(', ')}
                      </span>
                    </p>
                  )}
                  {supplierConfigStatus.partsWithoutSuppliers > 0 && (
                    <p>
                      <span className="font-medium">
                        {supplierConfigStatus.partsWithoutSuppliers} part(s)
                      </span>{' '}
                      have no supplier assigned
                    </p>
                  )}
                  <p className="text-secondary">
                    Configure suppliers in <span className="font-medium">Settings → Suppliers</span> to
                    enable enrichment and price updates.
                  </p>
                </div>
              </div>
              <button
                onClick={checkSupplierConfigStatus}
                className="btn btn-warning btn-sm ml-2"
                title="Refresh supplier status"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

      {/* Quick Actions */}
      <div className="card p-4">
        <h4 className="font-medium text-primary mb-3">Quick Actions</h4>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => createQuickTask('price-update')} className="btn btn-secondary btn-sm">
            <Zap className="w-4 h-4" />
            Update Prices
          </button>
          <button onClick={() => createQuickTask('bulk-enrichment')} className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4" />
            Enrich All Parts
          </button>
          <button onClick={() => createQuickTask('database-cleanup')} className="btn btn-secondary btn-sm">
            <Trash2 className="w-4 h-4" />
            Clean Database
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
            onChange={e => setStatusFilter(e.target.value)}
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
            onChange={e => setTypeFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="file_import_enrichment">File Import Enrichment</option>
            <option value="csv_enrichment">CSV Enrichment (Deprecated)</option>
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
            onChange={e => setPriorityFilter(e.target.value)}
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>

          <button onClick={resetFilters} className="btn btn-secondary btn-sm">
            Clear Filters
          </button>
        </div>
      </div>

      {/* Tasks List */}
      <div className="card">
        <div className="p-4 border-b border-border">
          <h4 className="font-medium text-primary">Tasks ({filteredTasks.length})</h4>
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
            filteredTasks.map(task => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-4 hover:bg-background-secondary transition-colors"
                data-testid={`task-${task.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(task.status)}
                      <h5 className="font-medium text-primary truncate">{task.name}</h5>
                      <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                      <span className="text-xs text-secondary">{formatTaskType(task.task_type)}</span>
                    </div>

                    {task.description && (
                      <p className="text-sm text-secondary truncate mb-2">{task.description}</p>
                    )}

                    {task.current_step && (
                      <p className="text-sm text-primary mb-2">{task.current_step}</p>
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

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="btn btn-secondary btn-sm"
                      title="View details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>

                    {task.status === 'running' && (
                      <button onClick={() => cancelTask(task.id)} className="btn btn-destructive btn-sm">
                        <Square className="w-4 h-4" />
                      </button>
                    )}

                    {task.status === 'failed' && (
                      <>
                        <button onClick={() => retryTask(task.id)} className="btn btn-primary btn-sm">
                          <RotateCcw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteTask(task.id)}
                          className="btn btn-destructive btn-sm"
                          title="Delete task"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}

                    {(task.status === 'completed' || task.status === 'cancelled') && (
                      <button
                        onClick={() => deleteTask(task.id)}
                        className="btn btn-destructive btn-sm"
                        title="Delete task"
                      >
                        <Trash2 className="w-4 h-4" />
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
              <button onClick={() => setConsoleVisible(false)} className="btn btn-secondary btn-sm">
                <XCircle className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 bg-background-primary dark:bg-black text-success font-mono text-sm min-h-[200px] max-h-[300px] overflow-y-auto custom-scrollbar">
              {consoleMessages.length === 0 ? (
                <div className="text-muted">Task console initialized - waiting for activity...</div>
              ) : (
                consoleMessages.map(msg => (
                  <div key={msg.id} className="mb-1">
                    <span className="text-info">[{msg.timestamp}]</span>
                    <span
                      className={`ml-2 ${
                        msg.type === 'success'
                          ? 'text-success'
                          : msg.type === 'warning'
                          ? 'text-warning'
                          : msg.type === 'error'
                          ? 'text-error'
                          : 'text-primary'
                      }`}
                    >
                      {msg.taskName ? `${msg.taskName}: ${msg.message}` : msg.message}
                    </span>
                  </div>
                ))
              )}

              {runningTasks.length > 0 ? (
                <>
                  <div className="text-accent mt-3 mb-1">--- Currently Running ---</div>
                  {runningTasks.map(task => (
                    <div key={`running-${task.id}`} className="mb-1">
                      <span className="text-info">[LIVE]</span>
                      <span className="text-warning"> {task.name}:</span>
                      <span className="text-success"> {task.current_step || 'Running...'}</span>
                      <span className="text-muted"> ({task.progress_percentage}%)</span>
                    </div>
                  ))}
                </>
              ) : (
                <div className="text-muted mt-3">No running tasks to monitor...</div>
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
                <h3 className="text-lg font-semibold text-primary">Task Details</h3>
                <button onClick={() => setSelectedTask(null)} className="btn btn-secondary btn-sm">
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
