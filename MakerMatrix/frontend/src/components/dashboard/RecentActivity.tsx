import { useState, useEffect, useCallback } from 'react'
import { Clock, Activity as ActivityIcon, RefreshCw } from 'lucide-react'
import type { Activity } from '@/services/activity.service'
import { activityService } from '@/services/activity.service'
import type { EntityEventData } from '@/services/websocket.service'
import { generalWebSocket } from '@/services/websocket.service'
import toast from 'react-hot-toast'

interface RecentActivityProps {
  limit?: number
  refreshInterval?: number // in milliseconds
}

const RecentActivity = ({ limit = 10, refreshInterval = 30000 }: RecentActivityProps) => {
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchActivities = async () => {
    try {
      const data = await activityService.getRecentActivities({
        limit,
        hours: 24, // Show activities from last 24 hours
      })
      setActivities(data)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch activities:', error)
      // Don't show toast on initial load failure to avoid spam
      if (!loading) {
        toast.error('Failed to update recent activity')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    await fetchActivities()
  }

  // Handle real-time activity updates via WebSocket
  const handleEntityEvent = useCallback(
    (data: EntityEventData) => {
      // Convert WebSocket entity event to Activity format
      const newActivity: Activity = {
        id: `${data.entity_id}-${Date.now()}`, // Generate temporary ID
        action: data.action,
        entity_type: data.entity_type,
        entity_id: data.entity_id,
        entity_name: data.entity_name,
        username: data.username || 'system',
        timestamp: data.timestamp,
        details: data.details || {},
      }

      // Add to the beginning of activities list
      setActivities((prev) => {
        const newActivities = [newActivity, ...prev]
        // Keep only the specified limit
        return newActivities.slice(0, limit)
      })

      // Update last updated time
      setLastUpdated(new Date())

      // TOAST NOTIFICATIONS PERMANENTLY DISABLED (2025-07-11)
      // Component-level toasts in modals provide better user feedback
      // This component is for activity tracking and display only
      console.log(
        'RecentActivity: Entity event received (NO TOAST):',
        data.action,
        data.entity_type,
        data.entity_name
      )
    },
    [limit]
  )

  useEffect(() => {
    fetchActivities()

    // Set up WebSocket listeners for real-time updates
    generalWebSocket.onEntityCreated(handleEntityEvent)
    generalWebSocket.onEntityUpdated(handleEntityEvent)
    generalWebSocket.onEntityDeleted(handleEntityEvent)

    // Set up auto-refresh if interval is provided (as fallback)
    let interval: NodeJS.Timeout | null = null
    if (refreshInterval > 0) {
      interval = setInterval(fetchActivities, refreshInterval)
    }

    return () => {
      // Cleanup WebSocket listeners
      generalWebSocket.off('entity_created', handleEntityEvent)
      generalWebSocket.off('entity_updated', handleEntityEvent)
      generalWebSocket.off('entity_deleted', handleEntityEvent)

      if (interval) {
        clearInterval(interval)
      }
    }
  }, [handleEntityEvent, refreshInterval])

  if (loading && activities.length === 0) {
    return (
      <div className="bg-background-primary rounded-lg p-6 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
            <ActivityIcon className="w-5 h-5" />
            Recent Activity
          </h3>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-background-secondary rounded-full"></div>
                <div className="flex-1">
                  <div className="h-4 bg-background-secondary rounded w-3/4 mb-1"></div>
                  <div className="h-3 bg-background-secondary rounded w-1/2"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-background-primary rounded-lg p-6 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
          <ActivityIcon className="w-5 h-5" />
          Recent Activity
        </h3>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-secondary flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {activityService.formatRelativeTime(lastUpdated.toISOString())}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-1 text-secondary hover:text-primary transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {activities.length === 0 ? (
          <div className="text-center py-8 text-secondary">
            <ActivityIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No recent activity</p>
            <p className="text-sm">Activities will appear here as you use the system</p>
          </div>
        ) : (
          activities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-start gap-3 p-3 rounded-lg bg-background-secondary hover:bg-background-secondary/80 transition-colors"
            >
              <div className="flex-shrink-0">
                <span className="text-lg">{activityService.getActivityIcon(activity)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p
                      className={`text-sm font-medium ${activityService.getActivityColor(activity)}`}
                    >
                      {activityService.formatActivityDescription(activity)}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-secondary">
                        by {activity.username || 'system'}
                      </span>
                      <span className="text-xs text-muted">•</span>
                      <span className="text-xs text-secondary">
                        {activityService.formatRelativeTime(activity.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Show additional details for certain activities */}
                {activity.details && Object.keys(activity.details).length > 0 && (
                  <div className="mt-2 text-xs text-muted">
                    {activity.action === 'printed' && activity.details.label_type && (
                      <span>Label type: {activity.details.label_type}</span>
                    )}
                    {activity.action === 'updated' && activity.details.changes && (
                      <span>Changed: {Object.keys(activity.details.changes).join(', ')}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {activities.length >= limit && (
        <div className="mt-4 pt-4 border-t border-border text-center">
          <button className="text-sm text-primary hover:text-primary-dark transition-colors">
            View all activity →
          </button>
        </div>
      )}
    </div>
  )
}

export default RecentActivity
