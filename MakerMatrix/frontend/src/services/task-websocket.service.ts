import type { WebSocketMessage } from './websocket.service'
import { WebSocketService } from './websocket.service'
import type { Task, WorkerStatus, TaskStats } from './tasks.service'

export interface TaskWebSocketMessage extends WebSocketMessage {
  type:
    | 'task_update'
    | 'task_created'
    | 'task_deleted'
    | 'worker_status_update'
    | 'task_stats_update'
    | 'ping'
    | 'pong'
    | 'error'
    | 'task_subscription'
    | 'task_unsubscription'
    | 'connection_info'
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
    const wrapped = (message: TaskWebSocketMessage) => {
      console.log('🔥 WebSocket received task_update:', message)
      if (message.data?.task) {
        handler(message.data.task)
      } else if (message.data) {
        // Handle case where task data is directly in message.data
        handler(message.data as Task)
      }
    }

    this.on('task_update', wrapped)
    return () => this.off('task_update', wrapped as any)
  }

  onTaskCreated(handler: (task: Task) => void) {
    const wrapped = (message: TaskWebSocketMessage) => {
      console.log('🆕 WebSocket received task_created:', message)
      if (message.data?.task) {
        handler(message.data.task)
      } else if (message.data) {
        handler(message.data as Task)
      }
    }

    this.on('task_created', wrapped)
    return () => this.off('task_created', wrapped as any)
  }

  onTaskDeleted(handler: (taskId: string) => void) {
    const wrapped = (message: TaskWebSocketMessage) => {
      if (message.data?.task_id) {
        handler(message.data.task_id)
      }
    }

    this.on('task_deleted', wrapped)
    return () => this.off('task_deleted', wrapped as any)
  }

  onWorkerStatusUpdate(handler: (status: WorkerStatus) => void) {
    const wrapped = (message: TaskWebSocketMessage) => {
      if (message.data?.worker_status) {
        handler(message.data.worker_status)
      }
    }

    this.on('worker_status_update', wrapped)
    return () => this.off('worker_status_update', wrapped as any)
  }

  onTaskStatsUpdate(handler: (stats: TaskStats) => void) {
    const wrapped = (message: TaskWebSocketMessage) => {
      if (message.data?.task_stats) {
        handler(message.data.task_stats)
      }
    }

    this.on('task_stats_update', wrapped)
    return () => this.off('task_stats_update', wrapped as any)
  }

  // Task subscription management
  subscribeToTask(taskId: string) {
    if (!this.subscribedTasks.has(taskId)) {
      this.subscribedTasks.add(taskId)
      this.sendMessage({
        type: 'subscribe_task',
        task_id: taskId,
        timestamp: new Date().toISOString(),
      })
    }
  }

  unsubscribeFromTask(taskId: string) {
    if (this.subscribedTasks.has(taskId)) {
      this.subscribedTasks.delete(taskId)
      this.sendMessage({
        type: 'unsubscribe_task',
        task_id: taskId,
        timestamp: new Date().toISOString(),
      })
    }
  }

  // Subscribe to all task updates - this happens automatically when connected to /ws/tasks

  // Get connection info
  getConnectionInfo() {
    this.sendMessage({
      type: 'get_connection_info',
      timestamp: new Date().toISOString(),
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
  taskWebSocket
    .connect()
    .then(() => {
      console.log('✅ Task WebSocket connected successfully')
    })
    .catch((error) => {
      console.error('❌ Task WebSocket connection failed:', error)
    })
  taskWebSocket.startHeartbeat()
}
