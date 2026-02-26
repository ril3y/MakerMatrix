import { apiClient, type ApiResponse } from './api'

export interface APIKeyCreate {
  name: string
  description?: string | null
  expires_in_days?: number | null
  role_names?: string[]
  permissions?: string[]
  allowed_ips?: string[]
}

export interface APIKey {
  id: string
  name: string
  description: string | null
  key_prefix: string
  user_id: string
  permissions: string[]
  role_names: string[]
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_used_at: string | null
  usage_count: number
  allowed_ips: string[]
  is_expired: boolean
  is_valid: boolean
}

export interface APIKeyWithKey extends APIKey {
  api_key: string // Only present when creating a new key
}

export interface AvailablePermission {
  value: string
  label: string
  category: string
}

class APIKeyService {
  /**
   * Get all API keys for the current user
   */
  async getUserApiKeys(): Promise<APIKey[]> {
    const response = await apiClient.get<ApiResponse<APIKey[]>>('/api/api-keys/')
    return response.data || []
  }

  /**
   * Create a new API key
   * Returns the key with plaintext api_key - only shown once!
   */
  async createApiKey(keyData: APIKeyCreate): Promise<APIKeyWithKey> {
    const response = await apiClient.post<ApiResponse<APIKeyWithKey>>('/api/api-keys/', keyData)
    return response.data as APIKeyWithKey
  }

  /**
   * Get a specific API key by ID
   */
  async getApiKey(keyId: string): Promise<APIKey> {
    const response = await apiClient.get<ApiResponse<APIKey>>(`/api/api-keys/${keyId}`)
    return response.data as APIKey
  }

  /**
   * Update an API key
   */
  async updateApiKey(keyId: string, updates: Partial<APIKeyCreate>): Promise<APIKey> {
    const response = await apiClient.put<ApiResponse<APIKey>>(`/api/api-keys/${keyId}`, updates)
    return response.data as APIKey
  }

  /**
   * Revoke (deactivate) an API key
   */
  async revokeApiKey(keyId: string): Promise<APIKey> {
    const response = await apiClient.post<ApiResponse<APIKey>>(`/api/api-keys/${keyId}/revoke`)
    return response.data as APIKey
  }

  /**
   * Permanently delete an API key
   */
  async deleteApiKey(keyId: string): Promise<void> {
    await apiClient.delete(`/api/api-keys/${keyId}`)
  }

  /**
   * Get all API keys in the system (admin only)
   */
  async getAllApiKeys(): Promise<APIKey[]> {
    const response = await apiClient.get<ApiResponse<APIKey[]>>('/api/api-keys/admin/all')
    return response.data || []
  }

  /**
   * Get all available permissions in the system
   * Dynamically fetched from backend based on role definitions
   */
  async getAvailablePermissions(): Promise<AvailablePermission[]> {
    const response = await apiClient.get<ApiResponse<AvailablePermission[]>>(
      '/api/api-keys/permissions/available'
    )
    return response.data || []
  }
}

export const apiKeyService = new APIKeyService()
