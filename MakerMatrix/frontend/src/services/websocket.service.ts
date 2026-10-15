export interface WebSocketMessage {
  type: string
  timestamp: string
  correlation_id?: string
  data: unknown
  metadata?: Record<string, unknown>
}

export interface EntityEventData {
  entity_type: string
  entity_id: string
  entity_name: string
  action: string
  user_id?: string
  username?: string
  timestamp: string
  changes?: Record<string, unknown>
  details: Record<string, unknown>
  entity_data?: Record<string, unknown>
}

export type WebSocketEventHandler = (message: WebSocketMessage) => void

export class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 1000
  private eventHandlers: Map<string, WebSocketEventHandler[]> = new Map()
  private isConnecting = false

  constructor(private endpoint: string = '/ws/general') {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
        resolve()
        return
      }

      this.isConnecting = true
      const token = localStorage.getItem('auth_token')

      const envApiUrl = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL
      const currentPort = window.location.port
      const currentProtocol = window.location.protocol

      let protocol = currentProtocol === 'https:' ? 'wss:' : 'ws:'
      let host = window.location.host
      let resolvedFromEnv = false

      if (envApiUrl) {
        try {
          const parsedUrl = new URL(envApiUrl)
          const { hostname, port, protocol: apiProtocol } = parsedUrl
          protocol = apiProtocol === 'https:' ? 'wss:' : 'ws:'
          host = `${hostname}${port ? `:${port}` : ''}`
          resolvedFromEnv = true
        } catch (error) {
          console.warn('⚠️ Failed to parse VITE_API_URL for WebSocket usage:', error)
        }
      }

      if (
        !resolvedFromEnv &&
        (currentPort === '5173' || currentPort === '5174' || currentPort === '3000')
      ) {
        // Fall back to default backend port in dev if env override is missing
        protocol = 'ws:'
        const backendPort = '8080'
        host = `${window.location.hostname}:${backendPort}`
      }

      const wsUrl = `${protocol}//${host}${this.endpoint}${token ? `?token=${token}` : ''}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.sendMessage({ type: 'subscribe_activities' })
        resolve()
      }

      this.ws.onclose = (event) => {
        this.isConnecting = false
        this.ws = null

        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          setTimeout(() => {
            this.reconnectAttempts++
            this.connect()
          }, this.reconnectInterval * this.reconnectAttempts)
        }
      }

      this.ws.onerror = (error) => {
        console.error(`❌ WebSocket error on ${this.endpoint}:`, error)
        this.isConnecting = false
        reject(error)
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  sendMessage(message: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, cannot send message:', message)
    }
  }

  // Event handler management
  on(eventType: string, handler: WebSocketEventHandler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, [])
    }
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      handlers.push(handler)
    }
  }

  off(eventType: string, handler: WebSocketEventHandler) {
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  private handleMessage(message: WebSocketMessage) {
    // Handle system messages
    if (message.type === 'pong') {
      return // Heartbeat response
    }

    if (message.type === 'connection') {
      return
    }

    // Emit to specific event handlers
    const handlers = this.eventHandlers.get(message.type)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in WebSocket event handler:', error)
        }
      })
    }

    // Emit to wildcard handlers
    const wildcardHandlers = this.eventHandlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in WebSocket wildcard handler:', error)
        }
      })
    }
  }

  // Utility methods for common events
  onEntityCreated(handler: (data: EntityEventData) => void) {
    this.on('entity_created', (message) => handler(message.data as EntityEventData))
  }

  onEntityUpdated(handler: (data: EntityEventData) => void) {
    this.on('entity_updated', (message) => handler(message.data as EntityEventData))
  }

  onEntityDeleted(handler: (data: EntityEventData) => void) {
    this.on('entity_deleted', (message) => handler(message.data as EntityEventData))
  }

  onPartCreated(handler: (data: EntityEventData) => void) {
    this.on('entity_created', (message) => {
      const data = message.data as EntityEventData
      if (data.entity_type === 'part') {
        handler(data)
      }
    })
  }

  onPartUpdated(handler: (data: EntityEventData) => void) {
    this.on('entity_updated', (message) => {
      const data = message.data as EntityEventData
      if (data.entity_type === 'part') {
        handler(data)
      }
    })
  }

  onPartDeleted(handler: (data: EntityEventData) => void) {
    this.on('entity_deleted', (message) => {
      const data = message.data as EntityEventData
      if (data.entity_type === 'part') {
        handler(data)
      }
    })
  }

  // Toast and notification handlers
  onToast(handler: (data: unknown) => void) {
    this.on('toast', (message) => handler(message.data))
  }

  onNotification(handler: (data: unknown) => void) {
    this.on('notification', (message) => handler(message.data))
  }

  // Heartbeat
  startHeartbeat(interval: number = 30000) {
    setInterval(() => {
      this.sendMessage({
        type: 'ping',
        timestamp: new Date().toISOString(),
      })
    }, interval)
  }

  // Connection status
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get connectionState(): string {
    if (!this.ws) return 'disconnected'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'open'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'closed'
      default:
        return 'unknown'
    }
  }
}

// Global instance for general activity updates
export const generalWebSocket = new WebSocketService('/ws/general')

// NOTE: Connection lifecycle is owned by `WebSocketProvider` (see
// `contexts/WebSocketContext.tsx`). Connecting at module load runs before
// `setAuthToken` has finished syncing localStorage on first login, so the
// initial WS handshake used to go out without a token — which is exactly
// why the login flow had to do a full-page reload. The provider now connects
// when the user becomes authenticated and disconnects on logout, so the
// auth-token-in-URL race is gone.
