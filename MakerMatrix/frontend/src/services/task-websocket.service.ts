import { WebSocketService, WebSocketMessage } from './websocket.service'
import { Task, WorkerStatus, TaskStats } from './tasks.service'

export interface TaskWebSocketMessage extends WebSocketMessage {
  type: 'task_update' | 'task_created' | 'task_deleted' | 'worker_status_update' | 'task_stats_update' | 'ping' | 'pong' | 'error' | 'task_subscription' | 'task_unsubscription' | 'connection_info'
  data: any
}

export interface TaskUpdateData {
  task: Task
}

export interface WorkerStatusUpdateData {
  worker_status: WorkerStatus
}

export interface TaskStatsUpdateData {
  task_stats: TaskStats
}

export type TaskEventHandler = (data: any) => void

export class TaskWebSocketService extends WebSocketService {
  private subscribedTasks: Set<string> = new Set()

  constructor() {
    super('/ws/tasks')
  }

  // Task-specific event handlers
  onTaskUpdate(handler: (task: Task) => void) {
    this.on('task_update', (message: TaskWebSocketMessage) => {
      console.log('🔥 WebSocket received task_update:', message)
      if (message.data?.task) {
        handler(message.data.task)
      } else if (message.data) {
        // Handle case where task data is directly in message.data
        handler(message.data as Task)
      }
    })
  }

  onTaskCreated(handler: (task: Task) => void) {
    this.on('task_created', (message: TaskWebSocketMessage) => {
      console.log('🆕 WebSocket received task_created:', message)
      if (message.data?.task) {
        handler(message.data.task)
      } else if (message.data) {
        handler(message.data as Task)
      }
    })
  }

  onTaskDeleted(handler: (taskId: string) => void) {
    this.on('task_deleted', (message: TaskWebSocketMessage) => {
      if (message.data?.task_id) {
        handler(message.data.task_id)
      }
    })
  }

  onWorkerStatusUpdate(handler: (status: WorkerStatus) => void) {
    this.on('worker_status_update', (message: TaskWebSocketMessage) => {
      if (message.data?.worker_status) {
        handler(message.data.worker_status)
      }
    })
  }

  onTaskStatsUpdate(handler: (stats: TaskStats) => void) {
    this.on('task_stats_update', (message: TaskWebSocketMessage) => {
      if (message.data?.task_stats) {
        handler(message.data.task_stats)
      }
    })
  }

  // Task subscription management
  subscribeToTask(taskId: string) {
    if (!this.subscribedTasks.has(taskId)) {
      this.subscribedTasks.add(taskId)
      this.sendMessage({
        type: 'subscribe_task',
        task_id: taskId,
        timestamp: new Date().toISOString()
      })
    }
  }

  unsubscribeFromTask(taskId: string) {
    if (this.subscribedTasks.has(taskId)) {
      this.subscribedTasks.delete(taskId)
      this.sendMessage({
        type: 'unsubscribe_task',
        task_id: taskId,
        timestamp: new Date().toISOString()
      })
    }
  }

  // Subscribe to all task updates - this happens automatically when connected to /ws/tasks

  // Get connection info
  getConnectionInfo() {
    this.sendMessage({
      type: 'get_connection_info',
      timestamp: new Date().toISOString()
    })
  }

  // Override disconnect to clean up subscriptions
  disconnect() {
    this.subscribedTasks.clear()
    super.disconnect()
  }

  // Get currently subscribed tasks
  getSubscribedTasks(): string[] {
    return Array.from(this.subscribedTasks)
  }
}

// Global instance for task WebSocket communication
export const taskWebSocket = new TaskWebSocketService()

// Auto-connect when module is imported
if (typeof window !== 'undefined') {
  // Add connection event logging
  taskWebSocket.connect().then(() => {
    console.log('✅ Task WebSocket connected successfully')
  }).catch((error) => {
    console.error('❌ Task WebSocket connection failed:', error)
  })
  taskWebSocket.startHeartbeat()
}