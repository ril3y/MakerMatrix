import { apiClient } from './api'

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

class APIKeyService {
  /**
   * Get all API keys for the current user
   */
  async getUserApiKeys(): Promise<APIKey[]> {
    const response = await apiClient.get('/api/api-keys/')
    return response.data?.data || []
  }

  /**
   * Create a new API key
   * Returns the key with plaintext api_key - only shown once!
   */
  async createApiKey(keyData: APIKeyCreate): Promise<APIKeyWithKey> {
    const response = await apiClient.post('/api/api-keys/', keyData)
    return response.data?.data
  }

  /**
   * Get a specific API key by ID
   */
  async getApiKey(keyId: string): Promise<APIKey> {
    const response = await apiClient.get(`/api/api-keys/${keyId}`)
    return response.data?.data
  }

  /**
   * Update an API key
   */
  async updateApiKey(keyId: string, updates: Partial<APIKeyCreate>): Promise<APIKey> {
    const response = await apiClient.put(`/api/api-keys/${keyId}`, updates)
    return response.data?.data
  }

  /**
   * Revoke (deactivate) an API key
   */
  async revokeApiKey(keyId: string): Promise<APIKey> {
    const response = await apiClient.post(`/api/api-keys/${keyId}/revoke`)
    return response.data?.data
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
    const response = await apiClient.get('/api/api-keys/admin/all')
    return response.data?.data || []
  }
}

export const apiKeyService = new APIKeyService()
