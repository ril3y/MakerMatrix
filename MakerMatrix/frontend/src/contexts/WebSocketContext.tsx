/**
 * WebSocket Context for Real-time Updates
 *
 * Provides WebSocket connection management and CRUD event handling
 * with toast notifications for all entity changes.
 */

import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useEffect,
  useCallback,
} from 'react'
import toast from 'react-hot-toast'
import { generalWebSocket, EntityEventData, WebSocketMessage } from '@/services/websocket.service'
import { useAuthStore } from '@/store/authStore'

export interface WebSocketContextType {
  isConnected: boolean
  connectionState: string
  reconnect: () => Promise<void>
  disconnect: () => void
  subscribe: (eventType: string, handler: (message: WebSocketMessage) => void) => void
  unsubscribe: (eventType: string, handler: (message: WebSocketMessage) => void) => void
  enableToasts: boolean
  setEnableToasts: (enabled: boolean) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
  enableToastsByDefault?: boolean
  showConnectionStatus?: boolean
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  enableToastsByDefault = true,
  showConnectionStatus = true,
}) => {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionState, setConnectionState] = useState('disconnected')
  const [enableToasts, setEnableToasts] = useState(enableToastsByDefault)
  const [hasShownConnectionToast, setHasShownConnectionToast] = useState(false)
  const { user } = useAuthStore()

  // Update connection state
  const updateConnectionState = useCallback(() => {
    const state = generalWebSocket.connectionState
    const connected = generalWebSocket.isConnected

    setConnectionState(state)
    setIsConnected(connected)

    // Show connection status toast only on changes
    if (showConnectionStatus && connected && !hasShownConnectionToast) {
      toast.success('Connected to real-time updates', {
        duration: 2000,
        position: 'bottom-right',
        icon: '🔗',
      })
      setHasShownConnectionToast(true)
    } else if (showConnectionStatus && !connected && hasShownConnectionToast) {
      toast.error('Disconnected from real-time updates', {
        duration: 3000,
        position: 'bottom-right',
        icon: '⚠️',
      })
      setHasShownConnectionToast(false)
    }
  }, [showConnectionStatus, hasShownConnectionToast])

  // Reconnect function
  const reconnect = useCallback(async () => {
    try {
      await generalWebSocket.connect()
      updateConnectionState()
    } catch (error) {
      console.error('Failed to reconnect WebSocket:', error)
      toast.error('Failed to reconnect to server')
    }
  }, [updateConnectionState])

  // Disconnect function
  const disconnect = useCallback(() => {
    generalWebSocket.disconnect()
    updateConnectionState()
  }, [updateConnectionState])

  // Subscribe to events
  const subscribe = useCallback(
    (eventType: string, handler: (message: WebSocketMessage) => void) => {
      generalWebSocket.on(eventType, handler)
    },
    []
  )

  // Unsubscribe from events
  const unsubscribe = useCallback(
    (eventType: string, handler: (message: WebSocketMessage) => void) => {
      generalWebSocket.off(eventType, handler)
    },
    []
  )

  // Get friendly entity type name
  const getEntityTypeName = (entityType: string): string => {
    const names: Record<string, string> = {
      part: 'Part',
      location: 'Location',
      category: 'Category',
      order: 'Order',
      task: 'Task',
      user: 'User',
    }
    return names[entityType] || entityType
  }

  // Get action verb
  const getActionVerb = (action: string): string => {
    const verbs: Record<string, string> = {
      created: 'created',
      updated: 'updated',
      deleted: 'deleted',
      bulk_updated: 'bulk updated',
    }
    return verbs[action] || action
  }

  // Get toast icon for action
  const getActionIcon = (action: string): string => {
    const icons: Record<string, string> = {
      created: '✨',
      updated: '🔄',
      deleted: '🗑️',
      bulk_updated: '📦',
    }
    return icons[action] || '📢'
  }

  // Handle CRUD events with toast notifications
  const handleCrudEvent = useCallback(
    (data: EntityEventData) => {
      if (!enableToasts) return

      // Don't show toast if the current user performed the action
      // (the component that made the change already shows a toast)
      if (data.username && user?.username && data.username === user.username) {
        console.log(
          '🔕 Skipping toast for own action:',
          data.action,
          data.entity_type,
          data.entity_name
        )
        return
      }

      const entityTypeName = getEntityTypeName(data.entity_type)
      const actionVerb = getActionVerb(data.action)
      const icon = getActionIcon(data.action)

      // Build toast message
      let message = `${entityTypeName} "${data.entity_name}" ${actionVerb}`

      // Add user context if available
      if (data.username) {
        message += ` by ${data.username}`
      }

      // Show toast based on action type
      switch (data.action) {
        case 'created':
          toast.success(message, {
            duration: 3000,
            position: 'bottom-right',
            icon,
          })
          break

        case 'updated':
          // Show change details if available
          let changeDetails = ''
          if (data.changes && Object.keys(data.changes).length > 0) {
            const changeCount = Object.keys(data.changes).length
            changeDetails = ` (${changeCount} field${changeCount > 1 ? 's' : ''} changed)`
          }

          toast(message + changeDetails, {
            duration: 3000,
            position: 'bottom-right',
            icon,
            style: {
              background: '#3b82f6',
              color: '#fff',
            },
          })
          break

        case 'deleted':
          toast.error(message, {
            duration: 3000,
            position: 'bottom-right',
            icon,
          })
          break

        case 'bulk_updated':
          // Special handling for bulk operations
          const count = data.details?.updated_count || 0
          const bulkMessage = `${count} ${entityTypeName.toLowerCase()}${count !== 1 ? 's' : ''} ${actionVerb}`

          toast.success(bulkMessage, {
            duration: 4000,
            position: 'bottom-right',
            icon,
          })
          break

        default:
          toast(message, {
            duration: 3000,
            position: 'bottom-right',
            icon,
          })
      }
    },
    [enableToasts, user?.username]
  )

  // Set up event listeners on mount
  useEffect(() => {
    // Check initial connection state
    updateConnectionState()

    // Set up connection state polling (for state changes not caught by events)
    const stateCheckInterval = setInterval(updateConnectionState, 5000)

    // Subscribe to all CRUD events
    const handleEntityCreated = (message: WebSocketMessage) => {
      handleCrudEvent(message.data)
    }

    const handleEntityUpdated = (message: WebSocketMessage) => {
      handleCrudEvent(message.data)
    }

    const handleEntityDeleted = (message: WebSocketMessage) => {
      handleCrudEvent(message.data)
    }

    const handleEntityBulkUpdated = (message: WebSocketMessage) => {
      handleCrudEvent(message.data)
    }

    generalWebSocket.on('entity_created', handleEntityCreated)
    generalWebSocket.on('entity_updated', handleEntityUpdated)
    generalWebSocket.on('entity_deleted', handleEntityDeleted)
    generalWebSocket.on('entity_bulk_updated', handleEntityBulkUpdated)

    // Cleanup on unmount
    return () => {
      clearInterval(stateCheckInterval)
      generalWebSocket.off('entity_created', handleEntityCreated)
      generalWebSocket.off('entity_updated', handleEntityUpdated)
      generalWebSocket.off('entity_deleted', handleEntityDeleted)
      generalWebSocket.off('entity_bulk_updated', handleEntityBulkUpdated)
    }
  }, [handleCrudEvent, updateConnectionState])

  const value: WebSocketContextType = {
    isConnected,
    connectionState,
    reconnect,
    disconnect,
    subscribe,
    unsubscribe,
    enableToasts,
    setEnableToasts,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

/**
 * Hook to use WebSocket context
 *
 * @example
 * const { isConnected, subscribe, unsubscribe } = useWebSocket()
 *
 * useEffect(() => {
 *   const handler = (message) => console.log('Event:', message)
 *   subscribe('entity_created', handler)
 *   return () => unsubscribe('entity_created', handler)
 * }, [])
 */
export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

/**
 * Hook to subscribe to specific entity events
 *
 * @example
 * useEntityEvents('part', {
 *   onCreate: (data) => console.log('Part created:', data),
 *   onUpdate: (data) => console.log('Part updated:', data),
 *   onDelete: (data) => console.log('Part deleted:', data)
 * })
 */
export const useEntityEvents = (
  entityType: string,
  handlers: {
    onCreate?: (data: EntityEventData) => void
    onUpdate?: (data: EntityEventData) => void
    onDelete?: (data: EntityEventData) => void
  }
) => {
  const { subscribe, unsubscribe } = useWebSocket()

  useEffect(() => {
    const createHandler = (message: WebSocketMessage) => {
      const data: EntityEventData = message.data
      if (data.entity_type === entityType && handlers.onCreate) {
        handlers.onCreate(data)
      }
    }

    const updateHandler = (message: WebSocketMessage) => {
      const data: EntityEventData = message.data
      if (data.entity_type === entityType && handlers.onUpdate) {
        handlers.onUpdate(data)
      }
    }

    const deleteHandler = (message: WebSocketMessage) => {
      const data: EntityEventData = message.data
      if (data.entity_type === entityType && handlers.onDelete) {
        handlers.onDelete(data)
      }
    }

    if (handlers.onCreate) {
      subscribe('entity_created', createHandler)
    }
    if (handlers.onUpdate) {
      subscribe('entity_updated', updateHandler)
    }
    if (handlers.onDelete) {
      subscribe('entity_deleted', deleteHandler)
    }

    return () => {
      if (handlers.onCreate) {
        unsubscribe('entity_created', createHandler)
      }
      if (handlers.onUpdate) {
        unsubscribe('entity_updated', updateHandler)
      }
      if (handlers.onDelete) {
        unsubscribe('entity_deleted', deleteHandler)
      }
    }
  }, [entityType, handlers, subscribe, unsubscribe])
}
