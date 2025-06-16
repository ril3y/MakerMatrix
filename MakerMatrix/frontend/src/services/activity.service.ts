import { apiClient, ApiResponse } from './api'

export interface Activity {
  id: string
  action: string
  entity_type: string
  entity_id?: string
  entity_name?: string
  username?: string
  timestamp: string
  details: Record<string, any>
}

export interface ActivityListResponse {
  activities: Activity[]
  total: number
}

export interface ActivityStats {
  total_activities: number
  by_action: Record<string, number>
  by_entity_type: Record<string, number>
  by_user: Record<string, number>
  most_active_hour?: string
}

export class ActivityService {
  async getRecentActivities(params?: {
    limit?: number
    entity_type?: string
    hours?: number
  }): Promise<Activity[]> {
    const queryParams = new URLSearchParams()
    
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.entity_type) queryParams.append('entity_type', params.entity_type)
    if (params?.hours) queryParams.append('hours', params.hours.toString())
    
    const response = await apiClient.get<ActivityListResponse>(
      `/api/activity/recent?${queryParams.toString()}`
    )
    
    return response.activities || []
  }

  async getActivityStats(hours: number = 24): Promise<ActivityStats> {
    const response = await apiClient.get<ActivityStats>(
      `/api/activity/stats?hours=${hours}`
    )
    
    return response
  }

  async cleanupOldActivities(keepDays: number = 90): Promise<{ deleted_count: number }> {
    const response = await apiClient.post<{ deleted_count: number }>(
      `/api/activity/cleanup?keep_days=${keepDays}`
    )
    
    return response
  }

  // Utility methods for formatting
  formatActivityAction(action: string): string {
    const actionMap: Record<string, string> = {
      'created': 'Created',
      'updated': 'Updated', 
      'deleted': 'Deleted',
      'printed': 'Printed',
      'registered': 'Registered',
      'imported': 'Imported',
      'exported': 'Exported',
      'logged_in': 'Logged in',
      'logged_out': 'Logged out'
    }
    
    return actionMap[action] || action.charAt(0).toUpperCase() + action.slice(1)
  }

  formatEntityType(entityType: string): string {
    const typeMap: Record<string, string> = {
      'part': 'Part',
      'printer': 'Printer',
      'label': 'Label',
      'location': 'Location',
      'category': 'Category',
      'user': 'User',
      'csv': 'CSV File'
    }
    
    return typeMap[entityType] || entityType.charAt(0).toUpperCase() + entityType.slice(1)
  }

  formatActivityDescription(activity: Activity): string {
    const action = this.formatActivityAction(activity.action)
    const entityType = this.formatEntityType(activity.entity_type)
    const entityName = activity.entity_name || `${entityType} ${activity.entity_id || ''}`
    
    return `${action} ${entityType}: ${entityName}`
  }

  getActivityIcon(activity: Activity): string {
    // Return emoji icons for different activity types
    const iconMap: Record<string, string> = {
      'created': '➕',
      'updated': '✏️',
      'deleted': '🗑️',
      'printed': '🖨️',
      'registered': '📝',
      'imported': '📥',
      'exported': '📤',
      'logged_in': '🔑',
      'logged_out': '🚪'
    }
    
    return iconMap[activity.action] || '📋'
  }

  getActivityColor(activity: Activity): string {
    // Return CSS color classes for different activities
    const colorMap: Record<string, string> = {
      'created': 'text-green-600',
      'updated': 'text-blue-600',
      'deleted': 'text-red-600',
      'printed': 'text-purple-600',
      'registered': 'text-indigo-600',
      'imported': 'text-orange-600',
      'exported': 'text-teal-600',
      'logged_in': 'text-green-500',
      'logged_out': 'text-gray-500'
    }
    
    return colorMap[activity.action] || 'text-gray-600'
  }

  formatRelativeTime(timestamp: string): string {
    const now = new Date()
    const activityTime = new Date(timestamp)
    const diffMs = now.getTime() - activityTime.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffMinutes < 1) {
      return 'Just now'
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m ago`
    } else if (diffHours < 24) {
      return `${diffHours}h ago`
    } else if (diffDays < 7) {
      return `${diffDays}d ago`
    } else {
      return activityTime.toLocaleDateString()
    }
  }
}

export const activityService = new ActivityService()