import { apiClient } from './api'

export interface AICommandResponse {
  action?: 'search-parts' | 'navigate' | 'query' | 'update'
  message?: string
  searchQuery?: string
  location?: string
  category?: string
  path?: string
  description?: string
  data?: any
}

export interface AIProcessRequest {
  command: string
  context?: {
    currentPage?: string
    selectedLocation?: number
    selectedCategory?: number
  }
}

class AIService {
  async processCommand(command: string, context?: any): Promise<AICommandResponse> {
    try {
      const response = await apiClient.post<AICommandResponse>('/api/ai/process-command', {
        command,
        context,
      })
      return response.data
    } catch (error) {
      console.error('AI service error:', error)
      // Fallback to local processing if API fails
      return this.processCommandLocally(command)
    }
  }

  private processCommandLocally(command: string): AICommandResponse {
    const lowerCommand = command.toLowerCase()

    // Parse find/search commands
    if (
      lowerCommand.includes('find') ||
      lowerCommand.includes('search') ||
      lowerCommand.includes('show')
    ) {
      // Extract location references
      const locationMatch = lowerCommand.match(
        /in\s+(?:the\s+)?([a-z0-9\s]+?)(?:\s+location)?(?:\s+drawer)?(?:\s+shelf)?$/i
      )
      const location = locationMatch ? locationMatch[1].trim() : undefined

      // Extract category references
      const categoryPatterns = ['resistor', 'capacitor', 'led', 'sensor', 'wire', 'connector']
      const category = categoryPatterns.find((cat) => lowerCommand.includes(cat))

      // Extract quantity references
      const lowStock =
        lowerCommand.includes('low') &&
        (lowerCommand.includes('stock') || lowerCommand.includes('quantity'))

      return {
        action: 'search-parts',
        searchQuery: lowStock ? '' : command.replace(/^(find|search|show)\s+/i, ''),
        location,
        category,
        description: command,
      }
    }

    // Parse navigation commands
    if (lowerCommand.includes('go to') || lowerCommand.includes('navigate')) {
      const pages = ['parts', 'locations', 'categories', 'settings', 'users']
      const page = pages.find((p) => lowerCommand.includes(p))
      if (page) {
        return {
          action: 'navigate',
          path: `/${page}`,
          message: `Navigating to ${page}`,
        }
      }
    }

    // Default response
    return {
      message: 'Command not recognized. Type "help" for available commands.',
    }
  }

  async generateLabel(partId: number): Promise<{ label_data: string }> {
    const response = await apiClient.post<{ label_data: string }>(
      `/api/ai/generate-label/${partId}`
    )
    return response
  }

  async suggestCategories(partName: string): Promise<string[]> {
    const response = await apiClient.post<{ categories: string[] }>('/api/ai/suggest-categories', {
      part_name: partName,
    })
    return response.categories
  }
}

export const aiService = new AIService()
