import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import type { Task, TaskStats, WorkerStatus } from '@/services/tasks.service'
import { tasksService } from '@/services/tasks.service'
import { partsService } from '@/services/parts.service'
import { taskWebSocket } from '@/services/task-websocket.service'

type ConsoleMessageType = 'info' | 'success' | 'warning' | 'error'

export interface ConsoleMessage {
  id: string
  timestamp: string
  type: ConsoleMessageType
  message: string
  taskName?: string
  taskId?: string
}

export interface SupplierConfigStatus {
  configured: string[]
  partsWithoutSuppliers: number
  unconfiguredSuppliers: string[]
  totalParts: number
}

const MAX_CONSOLE_MESSAGES = 50
const FALLBACK_REFRESH_MS = 2000

export function useTasksDashboard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const tasksRef = useRef<Task[]>([])
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([])
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null)
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [consoleMessages, setConsoleMessages] = useState<ConsoleMessage[]>([])
  const [supplierConfigStatus, setSupplierConfigStatus] = useState<SupplierConfigStatus | null>(
    null
  )
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(taskWebSocket.isConnected)

  const messageCounter = useRef(0)
  const fallbackIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const updateTasksState = useCallback((nextTasks: Task[]) => {
    tasksRef.current = nextTasks
    setTasks(nextTasks)
  }, [])

  const addConsoleMessage = useCallback(
    (type: ConsoleMessageType, message: string, taskName?: string, taskId?: string) => {
      messageCounter.current += 1
      const newMessage: ConsoleMessage = {
        id: `msg-${messageCounter.current}-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type,
        message,
        taskName,
        taskId,
      }

      setConsoleMessages((prev) => [...prev.slice(-(MAX_CONSOLE_MESSAGES - 1)), newMessage])
    },
    []
  )

  const checkSupplierConfigStatus = useCallback(async () => {
    try {
      const [allParts, configuredResponse, capabilitiesResponse] = await Promise.all([
        partsService.getAll(),
        fetch('/api/suppliers/configured', {
          headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
        }),
        fetch('/api/tasks/capabilities/suppliers', {
          headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
        }),
      ])

      const configuredSuppliers = configuredResponse.ok
        ? await configuredResponse.json()
        : { data: [] }
      const configuredNames = new Set(
        configuredSuppliers.data?.map((supplier: any) => {
          const supplierName = supplier.id || supplier.supplier_name || supplier.name || ''
          return supplierName.toUpperCase()
        }) || []
      )

      const availableSuppliers = capabilitiesResponse.ok
        ? await capabilitiesResponse.json()
        : { data: {} }
      const availableSupplierNames = new Set(
        Object.keys(availableSuppliers.data || {}).map((name) => name.toUpperCase())
      )

      const supplierCounts = new Map<string, number>()
      let partsWithoutSuppliers = 0
      let partsWithMetadataSuppliers = 0

      allParts.forEach((part) => {
        if (part.supplier) {
          if (availableSupplierNames.has(part.supplier.toUpperCase())) {
            supplierCounts.set(part.supplier, (supplierCounts.get(part.supplier) || 0) + 1)
          } else {
            partsWithMetadataSuppliers += 1
          }
        } else {
          partsWithoutSuppliers += 1
        }
      })

      const unconfiguredSuppliers = Array.from(supplierCounts.keys()).filter(
        (supplier) => !configuredNames.has(supplier.toUpperCase())
      )

      setSupplierConfigStatus({
        configured: Array.from(configuredNames),
        partsWithoutSuppliers,
        unconfiguredSuppliers,
        totalParts: allParts.length,
      })

      if (partsWithMetadataSuppliers > 0) {
        addConsoleMessage(
          'info',
          `Skipped ${partsWithMetadataSuppliers} parts with metadata-only suppliers (Amazon, etc.)`
        )
      }
    } catch (error) {
      console.error('Failed to check supplier configuration status:', error)
    }
  }, [addConsoleMessage])

  const loadWorkerStatus = useCallback(async () => {
    try {
      const status = await tasksService.getWorkerStatus()
      setWorkerStatus(status.data)
    } catch (error: any) {
      if (error?.response?.status !== 404) {
        console.error('Failed to load worker status:', error)
      }
    }
  }, [])

  const loadTaskStats = useCallback(async () => {
    try {
      const stats = await tasksService.getTaskStats()
      setTaskStats(stats.data)
    } catch (error: any) {
      if (error?.response?.status !== 404) {
        console.error('Failed to load task stats:', error)
      }
    }
  }, [])

  const formatDuration = useCallback((startTime?: string, endTime?: string) => {
    if (!startTime) return 'Not started'

    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()
    const duration = Math.round((end.getTime() - start.getTime()) / 1000)

    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.round(duration / 60)}m`
    return `${Math.round(duration / 3600)}h`
  }, [])

  const loadTasks = useCallback(async () => {
    try {
      const response = await tasksService.getTasks()
      const newTasks = response.data || []
      const previousTasks = tasksRef.current

      if (previousTasks.length > 0) {
        newTasks.forEach((newTask) => {
          const oldTask = previousTasks.find((task) => task.id === newTask.id)

          if (!oldTask) {
            addConsoleMessage(
              'success',
              `Task discovered: ${newTask.status}`,
              newTask.name,
              newTask.id
            )
            if (newTask.status === 'running') {
              addConsoleMessage('info', 'Task is running...', newTask.name, newTask.id)
            } else if (newTask.status === 'completed') {
              const duration = formatDuration(newTask.started_at, newTask.completed_at)
              addConsoleMessage(
                'success',
                `Task completed in ${duration}`,
                newTask.name,
                newTask.id
              )
            } else if (newTask.status === 'failed') {
              addConsoleMessage(
                'error',
                `Task failed: ${newTask.error_message || 'Unknown error'}`,
                newTask.name,
                newTask.id
              )
            }
          } else if (oldTask.status !== newTask.status) {
            const statusMessage = `Status: ${oldTask.status} → ${newTask.status}`

            if (newTask.status === 'completed') {
              const duration = formatDuration(newTask.started_at, newTask.completed_at)
              addConsoleMessage(
                'success',
                `${statusMessage} (${duration})`,
                newTask.name,
                newTask.id
              )
            } else if (newTask.status === 'failed') {
              addConsoleMessage(
                'error',
                `${statusMessage}: ${newTask.error_message || 'Unknown error'}`,
                newTask.name,
                newTask.id
              )
            } else if (newTask.status === 'running') {
              addConsoleMessage('info', 'Task started running', newTask.name, newTask.id)
            } else {
              addConsoleMessage('info', statusMessage, newTask.name, newTask.id)
            }
          } else if (
            oldTask.progress_percentage !== newTask.progress_percentage &&
            newTask.status === 'running'
          ) {
            addConsoleMessage(
              'info',
              `Progress: ${newTask.progress_percentage}% - ${newTask.current_step || 'Processing...'}`,
              newTask.name,
              newTask.id
            )
          }
        })

        previousTasks.forEach((oldTask) => {
          if (!newTasks.find((task) => task.id === oldTask.id)) {
            addConsoleMessage('warning', 'Task removed from list', oldTask.name, oldTask.id)
          }
        })
      } else if (newTasks.length > 0) {
        addConsoleMessage('info', `Loaded ${newTasks.length} existing tasks`)
      }

      updateTasksState(newTasks)
    } catch (error: any) {
      console.error('Failed to load tasks:', error)
      if (!tasksRef.current.length && error?.response?.status !== 404) {
        toast.error('Failed to load tasks')
      }
    } finally {
      setLoading(false)
    }
  }, [addConsoleMessage, formatDuration, updateTasksState])

  const startWorker = useCallback(async () => {
    try {
      await tasksService.startWorker()
      toast.success('Task worker started')
      loadWorkerStatus()
    } catch (error) {
      toast.error('Failed to start worker')
    }
  }, [loadWorkerStatus])

  const stopWorker = useCallback(async () => {
    try {
      await tasksService.stopWorker()
      toast.success('Task worker stopped')
      loadWorkerStatus()
    } catch (error) {
      toast.error('Failed to stop worker')
    }
  }, [loadWorkerStatus])

  const cancelTask = useCallback(
    async (taskId: string) => {
      try {
        await tasksService.cancelTask(taskId)
        toast.success('Task cancelled')
        loadTasks()
      } catch (error) {
        toast.error('Failed to cancel task')
      }
    },
    [loadTasks]
  )

  const retryTask = useCallback(
    async (taskId: string) => {
      try {
        await tasksService.retryTask(taskId)
        toast.success('Task retry scheduled')
        loadTasks()
      } catch (error) {
        toast.error('Failed to retry task')
      }
    },
    [loadTasks]
  )

  const deleteTask = useCallback(
    async (taskId: string) => {
      if (
        !window.confirm('Are you sure you want to delete this task? This action cannot be undone.')
      ) {
        return
      }

      try {
        await tasksService.deleteTask(taskId)
        toast.success('Task deleted successfully')
        loadTasks()
      } catch (error) {
        toast.error('Failed to delete task')
      }
    },
    [loadTasks]
  )

  const ensureSupplierConfiguration = useCallback(
    async (supplierCounts: Map<string, number>) => {
      try {
        const response = await fetch('/api/suppliers/configured', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
        })

        if (!response.ok) {
          addConsoleMessage(
            'error',
            `Failed to check supplier configurations: ${response.status} ${response.statusText}`
          )
          toast.error('Failed to verify supplier configurations. Please try again.')
          return false
        }

        const configuredSuppliers = await response.json()
        const configuredNames = new Set(
          configuredSuppliers.data?.map((supplier: any) => {
            const supplierName = supplier.id || supplier.supplier_name || supplier.name || ''
            return supplierName.toUpperCase()
          }) || []
        )

        const unconfiguredSuppliers = Array.from(supplierCounts.keys()).filter(
          (supplier) => !configuredNames.has(supplier.toUpperCase())
        )

        if (unconfiguredSuppliers.length > 0) {
          addConsoleMessage(
            'error',
            `Unconfigured suppliers detected: ${unconfiguredSuppliers.join(', ')}`
          )
          toast.error(
            `Cannot enrich parts - ${unconfiguredSuppliers.length} supplier(s) need configuration: ${unconfiguredSuppliers.join(', ')}`
          )
          addConsoleMessage(
            'info',
            'Please configure suppliers in Settings → Suppliers before attempting enrichment'
          )
          return false
        }

        addConsoleMessage('success', 'All suppliers are configured for enrichment')
        return true
      } catch (error: any) {
        console.error('Error checking supplier configurations:', error)
        addConsoleMessage('error', `Error checking supplier configurations: ${error.message}`)
        toast.error(
          'Could not verify supplier configurations. Please check your connection and try again.'
        )
        return false
      }
    },
    [addConsoleMessage]
  )

  const createQuickTask = useCallback(
    async (taskType: string) => {
      try {
        let taskData: Record<string, unknown> = {}

        switch (taskType) {
          case 'price-update': {
            toast.loading('Checking parts for price updates...', { id: 'price-update-loading' })
            const allParts = await partsService.getAll()

            if (allParts.length === 0) {
              toast.dismiss('price-update-loading')
              toast.error('No parts found for price updates')
              return
            }

            const capabilitiesResponse = await fetch('/api/tasks/capabilities/suppliers', {
              headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            })

            const availableSuppliers = capabilitiesResponse.ok
              ? await capabilitiesResponse.json()
              : { data: {} }
            const availableSupplierNames = new Set(
              Object.keys(availableSuppliers.data || {}).map((name) => name.toUpperCase())
            )

            const supplierCounts = new Map<string, number>()
            let partsWithMetadataSuppliers = 0

            allParts.forEach((part) => {
              if (part.supplier) {
                if (availableSupplierNames.has(part.supplier.toUpperCase())) {
                  supplierCounts.set(part.supplier, (supplierCounts.get(part.supplier) || 0) + 1)
                } else {
                  partsWithMetadataSuppliers += 1
                }
              }
            })

            toast.dismiss('price-update-loading')

            if (supplierCounts.size === 0) {
              const message =
                partsWithMetadataSuppliers > 0
                  ? `No parts have enrichable suppliers. Found ${partsWithMetadataSuppliers} parts with metadata-only suppliers (Amazon, etc.)`
                  : 'No parts have suppliers assigned. Cannot update prices without supplier information.'
              toast.error(message)
              addConsoleMessage('error', `Price update failed: ${message}`)
              return
            }

            const supplierList = Array.from(supplierCounts.entries())
              .map(([supplier, count]) => `${supplier}: ${count} parts`)
              .join(', ')

            addConsoleMessage('info', `Found parts from enrichable suppliers: ${supplierList}`)
            if (partsWithMetadataSuppliers > 0) {
              addConsoleMessage(
                'info',
                `Skipped ${partsWithMetadataSuppliers} parts with metadata-only suppliers (Amazon, etc.)`
              )
            }
            addConsoleMessage(
              'warning',
              'Note: Price updates require supplier configurations to be set up in Settings → Suppliers'
            )

            const ready = await ensureSupplierConfiguration(supplierCounts)
            if (!ready) {
              return
            }

            taskData = { update_all: true }
            toast.success(
              `Found ${allParts.length} parts for price updates from ${supplierCounts.size} suppliers`
            )
            break
          }
          case 'bulk-enrichment': {
            toast.loading('Fetching parts for enrichment...', { id: 'bulk-enrichment-loading' })
            const allParts = await partsService.getAll()

            if (allParts.length === 0) {
              toast.dismiss('bulk-enrichment-loading')
              toast.error('No parts available for enrichment')
              return
            }

            const capabilitiesResponse = await fetch('/api/tasks/capabilities/suppliers', {
              headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
            })

            const availableSuppliers = capabilitiesResponse.ok
              ? await capabilitiesResponse.json()
              : { data: {} }
            const availableSupplierNames = new Set(
              Object.keys(availableSuppliers.data || {}).map((name) => name.toUpperCase())
            )

            const supplierCounts = new Map<string, number>()
            let partsWithMetadataSuppliers = 0
            const partIds: string[] = []

            allParts.forEach((part) => {
              partIds.push(part.id)
              if (part.supplier) {
                if (availableSupplierNames.has(part.supplier.toUpperCase())) {
                  supplierCounts.set(part.supplier, (supplierCounts.get(part.supplier) || 0) + 1)
                } else {
                  partsWithMetadataSuppliers += 1
                }
              }
            })

            toast.dismiss('bulk-enrichment-loading')

            if (supplierCounts.size === 0) {
              const message =
                partsWithMetadataSuppliers > 0
                  ? `No parts have enrichable suppliers. Found ${partsWithMetadataSuppliers} parts with metadata-only suppliers (Amazon, etc.)`
                  : 'No parts have suppliers assigned. Cannot enrich parts without supplier information.'
              toast.error(message)
              addConsoleMessage('error', `Enrichment failed: ${message}`)
              return
            }

            const supplierList = Array.from(supplierCounts.entries())
              .map(([supplier, count]) => `${supplier}: ${count} parts`)
              .join(', ')

            addConsoleMessage('info', `Found parts from enrichable suppliers: ${supplierList}`)
            if (partsWithMetadataSuppliers > 0) {
              addConsoleMessage(
                'info',
                `Skipped ${partsWithMetadataSuppliers} parts with metadata-only suppliers (Amazon, etc.)`
              )
            }
            addConsoleMessage(
              'warning',
              'Note: Enrichment requires supplier configurations to be set up in Settings → Suppliers'
            )

            const ready = await ensureSupplierConfiguration(supplierCounts)
            if (!ready) {
              return
            }

            taskData = {
              enrich_all: true,
              batch_size: 10,
              page_size: 10,
              capabilities: [
                'fetch_pricing',
                'fetch_datasheet',
                'fetch_specifications',
                'fetch_image',
              ],
              force_refresh: false,
            }
            toast.success(
              `Found ${partIds.length} parts for enrichment from ${supplierCounts.size} suppliers. Task will process 10 parts at a time.`
            )
            break
          }
          case 'database-cleanup': {
            taskData = { cleanup_type: 'full' }
            break
          }
          default: {
            taskData = {}
          }
        }

        const taskName = `${taskType
          .split('-')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ')} Task`

        addConsoleMessage('info', `Creating ${taskName}...`)
        const response = await tasksService.createQuickTask(taskType, taskData)
        addConsoleMessage(
          'success',
          `${taskName} created successfully`,
          taskName,
          response.data?.id
        )
        toast.success('Task created successfully')

        await Promise.all([loadTasks(), loadWorkerStatus(), loadTaskStats()])
      } catch (error: any) {
        console.error('Failed to create task:', error)
        const detail = error?.response?.data?.detail || error.message
        const taskName = `${taskType
          .split('-')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ')} Task`
        addConsoleMessage('error', `Failed to create ${taskName}: ${detail}`)
        toast.error(`Failed to create task: ${detail}`)
      } finally {
        toast.dismiss('price-update-loading')
        toast.dismiss('bulk-enrichment-loading')
      }
    },
    [addConsoleMessage, ensureSupplierConfiguration, loadTaskStats, loadTasks, loadWorkerStatus]
  )

  const toggleAutoRefresh = useCallback(() => {
    setAutoRefresh((prev) => !prev)
  }, [])

  const reconnectWebSocket = useCallback(async () => {
    try {
      taskWebSocket.disconnect()
      await taskWebSocket.connect()
      setIsWebSocketConnected(true)
      toast.success('WebSocket reconnected')
    } catch (error) {
      console.error('WebSocket reconnection failed:', error)
      setIsWebSocketConnected(false)
      toast.error('WebSocket reconnection failed')
    }
  }, [])

  useEffect(() => {
    loadTasks()
    loadWorkerStatus()
    loadTaskStats()
    checkSupplierConfigStatus()

    const handleTaskUpdate = (task: Task) => {
      setIsWebSocketConnected(true)
      addConsoleMessage(
        'info',
        `${task.current_step || 'Processing...'} (${task.progress_percentage}%)`,
        task.name,
        task.id
      )

      setTasks((prevTasks) => {
        const existingIndex = prevTasks.findIndex((t) => t.id === task.id)
        let updatedTasks: Task[]

        if (existingIndex >= 0) {
          updatedTasks = [...prevTasks]
          updatedTasks[existingIndex] = task
        } else {
          updatedTasks = [...prevTasks, task]
        }

        tasksRef.current = updatedTasks
        return updatedTasks
      })
    }

    const handleTaskCreated = (task: Task) => {
      setIsWebSocketConnected(true)
      addConsoleMessage('success', 'Task created', task.name, task.id)
      setTasks((prevTasks) => {
        if (prevTasks.find((t) => t.id === task.id)) {
          return prevTasks
        }
        const updatedTasks = [...prevTasks, task]
        tasksRef.current = updatedTasks
        return updatedTasks
      })
      toast.success(`Task "${task.name}" created`)
    }

    const handleTaskDeleted = (taskId: string) => {
      setIsWebSocketConnected(true)
      const deletedTask = tasksRef.current.find((t) => t.id === taskId)
      addConsoleMessage('warning', 'Task deleted', deletedTask?.name, taskId)
      setTasks((prevTasks) => {
        const updatedTasks = prevTasks.filter((t) => t.id !== taskId)
        tasksRef.current = updatedTasks
        return updatedTasks
      })
      toast.info('Task deleted')
    }

    const handleWorkerStatusUpdate = (status: WorkerStatus) => {
      setIsWebSocketConnected(true)
      const message = status.is_running ? 'Worker started' : 'Worker stopped'
      addConsoleMessage('info', `${message} (${status.running_tasks_count} tasks running)`)
      setWorkerStatus(status)
    }

    const handleTaskStatsUpdate = (stats: TaskStats) => {
      setIsWebSocketConnected(true)
      setTaskStats(stats)
    }

    const unsubscribeTaskUpdate = taskWebSocket.onTaskUpdate(handleTaskUpdate)
    const unsubscribeTaskCreated = taskWebSocket.onTaskCreated(handleTaskCreated)
    const unsubscribeTaskDeleted = taskWebSocket.onTaskDeleted(handleTaskDeleted)
    const unsubscribeWorkerStatus = taskWebSocket.onWorkerStatusUpdate(handleWorkerStatusUpdate)
    const unsubscribeTaskStats = taskWebSocket.onTaskStatsUpdate(handleTaskStatsUpdate)

    setIsWebSocketConnected(taskWebSocket.isConnected)
    const connectionStatus = taskWebSocket.isConnected
      ? 'WebSocket connected'
      : 'WebSocket disconnected - using polling'
    addConsoleMessage(taskWebSocket.isConnected ? 'success' : 'warning', connectionStatus)

    if (autoRefresh && !taskWebSocket.isConnected) {
      fallbackIntervalRef.current = setInterval(() => {
        if (!taskWebSocket.isConnected) {
          setIsWebSocketConnected(false)
          loadTasks()
          loadWorkerStatus()
          loadTaskStats()
        }
      }, FALLBACK_REFRESH_MS)
    }

    return () => {
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current)
        fallbackIntervalRef.current = null
      }

      unsubscribeTaskUpdate?.()
      unsubscribeTaskCreated?.()
      unsubscribeTaskDeleted?.()
      unsubscribeWorkerStatus?.()
      unsubscribeTaskStats?.()
    }
  }, [
    addConsoleMessage,
    autoRefresh,
    checkSupplierConfigStatus,
    loadTaskStats,
    loadTasks,
    loadWorkerStatus,
  ])

  useEffect(() => {
    let filtered = tasks

    if (statusFilter !== 'all') {
      filtered = filtered.filter((task) => task.status === statusFilter)
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter((task) => task.task_type === typeFilter)
    }

    if (priorityFilter !== 'all') {
      filtered = filtered.filter((task) => task.priority === priorityFilter)
    }

    setFilteredTasks(filtered)
  }, [priorityFilter, statusFilter, tasks, typeFilter])

  const resetFilters = useCallback(() => {
    setStatusFilter('all')
    setTypeFilter('all')
    setPriorityFilter('all')
  }, [])

  return {
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
    reconnectWebSocket,
    loadTasks,
  }
}

export type UseTasksDashboardReturn = ReturnType<typeof useTasksDashboard>
