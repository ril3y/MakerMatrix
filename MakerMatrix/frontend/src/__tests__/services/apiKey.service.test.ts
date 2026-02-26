import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiKeyService } from '../../services/apiKey.service'
import { apiClient } from '../../services/api'
import type { APIKey, APIKeyWithKey, AvailablePermission } from '../../services/apiKey.service'

// Mock the API client
vi.mock('../../services/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// --- Mock data ---

const mockApiKey: APIKey = {
  id: 'key-1',
  name: 'Test API Key',
  description: 'A key for testing',
  key_prefix: 'mm_test_',
  user_id: 'user-1',
  permissions: ['parts:read', 'parts:write'],
  role_names: ['user'],
  is_active: true,
  expires_at: null,
  created_at: '2025-06-01T00:00:00Z',
  last_used_at: null,
  usage_count: 0,
  allowed_ips: [],
  is_expired: false,
  is_valid: true,
}

const mockApiKey2: APIKey = {
  ...mockApiKey,
  id: 'key-2',
  name: 'Second API Key',
  user_id: 'user-2',
}

const mockApiKeyWithKey: APIKeyWithKey = {
  ...mockApiKey,
  api_key: 'mm_test_abc123def456',
}

const mockPermission1: AvailablePermission = {
  value: 'parts:read',
  label: 'Read Parts',
  category: 'Parts',
}

const mockPermission2: AvailablePermission = {
  value: 'parts:write',
  label: 'Write Parts',
  category: 'Parts',
}

const mockPermission3: AvailablePermission = {
  value: 'admin:access',
  label: 'Admin Access',
  category: 'Admin',
}

describe('APIKeyService - ResponseSchema unwrapping', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getUserApiKeys', () => {
    it('returns an array, not a ResponseSchema wrapper', async () => {
      const mockKeys = [mockApiKey, mockApiKey2]

      // apiClient.get already strips the Axios response layer,
      // so it returns the ResponseSchema body: { status, message, data }
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'API keys retrieved',
        data: mockKeys,
      })

      const result = await apiKeyService.getUserApiKeys()

      // The result must be the unwrapped array, NOT the ResponseSchema wrapper
      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual(mockKeys)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
    })

    it('returns an empty array when data is undefined', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'No API keys found',
        // data is undefined
      })

      const result = await apiKeyService.getUserApiKeys()

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual([])
    })

    it('returns values that are iterable with .map()', async () => {
      const mockKeys = [mockApiKey, mockApiKey2]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'API keys retrieved',
        data: mockKeys,
      })

      const result = await apiKeyService.getUserApiKeys()

      // This is the exact operation that would fail if the ResponseSchema
      // wrapper was returned instead of the array. Calling .map() on
      // { status, message, data } throws "result.map is not a function".
      const names = result.map((key) => key.name)
      expect(names).toEqual(['Test API Key', 'Second API Key'])
    })

    it('calls the correct API endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [],
      })

      await apiKeyService.getUserApiKeys()

      expect(apiClient.get).toHaveBeenCalledWith('/api/api-keys/')
    })
  })

  describe('getAllApiKeys', () => {
    it('returns an array, not a ResponseSchema wrapper', async () => {
      const mockKeys = [mockApiKey, mockApiKey2]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'All API keys retrieved',
        data: mockKeys,
      })

      const result = await apiKeyService.getAllApiKeys()

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual(mockKeys)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
    })

    it('returns an empty array when data is undefined', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'No keys',
      })

      const result = await apiKeyService.getAllApiKeys()

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual([])
    })

    it('returns values that are iterable with .map()', async () => {
      const mockKeys = [mockApiKey, mockApiKey2]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: mockKeys,
      })

      const result = await apiKeyService.getAllApiKeys()

      const ids = result.map((key) => key.id)
      expect(ids).toEqual(['key-1', 'key-2'])
    })

    it('calls the correct admin API endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [],
      })

      await apiKeyService.getAllApiKeys()

      expect(apiClient.get).toHaveBeenCalledWith('/api/api-keys/admin/all')
    })
  })

  describe('getAvailablePermissions', () => {
    it('returns an array, not a ResponseSchema wrapper', async () => {
      const mockPermissions = [mockPermission1, mockPermission2, mockPermission3]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'Permissions retrieved',
        data: mockPermissions,
      })

      const result = await apiKeyService.getAvailablePermissions()

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual(mockPermissions)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
    })

    it('returns an empty array when data is undefined', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'No permissions',
      })

      const result = await apiKeyService.getAvailablePermissions()

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual([])
    })

    it('returns values that are iterable with .map()', async () => {
      const mockPermissions = [mockPermission1, mockPermission2, mockPermission3]

      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: mockPermissions,
      })

      const result = await apiKeyService.getAvailablePermissions()

      const categories = result.map((perm) => perm.category)
      expect(categories).toEqual(['Parts', 'Parts', 'Admin'])
    })

    it('calls the correct API endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [],
      })

      await apiKeyService.getAvailablePermissions()

      expect(apiClient.get).toHaveBeenCalledWith('/api/api-keys/permissions/available')
    })
  })

  describe('createApiKey', () => {
    it('returns the unwrapped API key data, not a ResponseSchema wrapper', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'API key created',
        data: mockApiKeyWithKey,
      })

      const result = await apiKeyService.createApiKey({
        name: 'Test API Key',
        permissions: ['parts:read', 'parts:write'],
      })

      // Must be the unwrapped APIKeyWithKey, not the ResponseSchema
      expect(result).toEqual(mockApiKeyWithKey)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
      expect(result.api_key).toBe('mm_test_abc123def456')
      expect(result.name).toBe('Test API Key')
    })

    it('returns a value with api_key field accessible', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'API key created',
        data: mockApiKeyWithKey,
      })

      const result = await apiKeyService.createApiKey({
        name: 'Test API Key',
      })

      // If the ResponseSchema wrapper was returned, result.api_key would be undefined
      // because the wrapper has { status, message, data } not { api_key, ... }
      expect(result.api_key).toBeDefined()
      expect(typeof result.api_key).toBe('string')
    })

    it('calls the correct API endpoint with provided data', async () => {
      const createData = {
        name: 'My Key',
        description: 'Key description',
        expires_in_days: 30,
        permissions: ['parts:read'],
        allowed_ips: ['192.168.1.0/24'],
      }

      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: mockApiKeyWithKey,
      })

      await apiKeyService.createApiKey(createData)

      expect(apiClient.post).toHaveBeenCalledWith('/api/api-keys/', createData)
    })
  })

  describe('getApiKey', () => {
    it('returns the unwrapped API key, not a ResponseSchema wrapper', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'API key retrieved',
        data: mockApiKey,
      })

      const result = await apiKeyService.getApiKey('key-1')

      expect(result).toEqual(mockApiKey)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
      expect(result.id).toBe('key-1')
    })

    it('calls the correct API endpoint', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: mockApiKey,
      })

      await apiKeyService.getApiKey('key-1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/api-keys/key-1')
    })
  })

  describe('updateApiKey', () => {
    it('returns the unwrapped updated API key', async () => {
      const updatedKey = { ...mockApiKey, name: 'Updated Key Name' }

      vi.mocked(apiClient.put).mockResolvedValue({
        status: 'success',
        message: 'API key updated',
        data: updatedKey,
      })

      const result = await apiKeyService.updateApiKey('key-1', { name: 'Updated Key Name' })

      expect(result).toEqual(updatedKey)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
      expect(result.name).toBe('Updated Key Name')
    })

    it('calls the correct API endpoint with updates', async () => {
      const updates = { name: 'New Name', description: 'New description' }

      vi.mocked(apiClient.put).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: { ...mockApiKey, ...updates },
      })

      await apiKeyService.updateApiKey('key-1', updates)

      expect(apiClient.put).toHaveBeenCalledWith('/api/api-keys/key-1', updates)
    })
  })

  describe('revokeApiKey', () => {
    it('returns the unwrapped revoked API key', async () => {
      const revokedKey = { ...mockApiKey, is_active: false, is_valid: false }

      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'API key revoked',
        data: revokedKey,
      })

      const result = await apiKeyService.revokeApiKey('key-1')

      expect(result).toEqual(revokedKey)
      expect(result).not.toHaveProperty('status')
      expect(result).not.toHaveProperty('message')
      expect(result.is_active).toBe(false)
    })

    it('calls the correct API endpoint', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: { ...mockApiKey, is_active: false },
      })

      await apiKeyService.revokeApiKey('key-1')

      expect(apiClient.post).toHaveBeenCalledWith('/api/api-keys/key-1/revoke')
    })
  })

  describe('deleteApiKey', () => {
    it('calls the correct API endpoint', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue(undefined)

      await apiKeyService.deleteApiKey('key-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/api-keys/key-1')
    })
  })

  describe('ResponseSchema unwrapping regression guard', () => {
    /**
     * These tests specifically guard against the bug pattern where service methods
     * return `response` (the full ResponseSchema wrapper) instead of `response.data`
     * (the unwrapped payload).
     *
     * When the bug is present:
     *   - result has { status: 'success', message: '...', data: [...] }
     *   - result.map() throws "result.map is not a function"
     *   - result[0] is undefined (objects don't have numeric indices)
     *   - Array.isArray(result) returns false
     *
     * When the bug is fixed:
     *   - result is the actual array or object from .data
     *   - Array methods work correctly
     */

    it('getUserApiKeys result does not have ResponseSchema properties', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockApiKey],
      })

      const result = await apiKeyService.getUserApiKeys()

      // If the wrapper was returned, these would be truthy
      expect((result as unknown as Record<string, unknown>).status).toBeUndefined()
      expect((result as unknown as Record<string, unknown>).message).toBeUndefined()
    })

    it('getAllApiKeys result does not have ResponseSchema properties', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockApiKey],
      })

      const result = await apiKeyService.getAllApiKeys()

      expect((result as unknown as Record<string, unknown>).status).toBeUndefined()
      expect((result as unknown as Record<string, unknown>).message).toBeUndefined()
    })

    it('getAvailablePermissions result does not have ResponseSchema properties', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockPermission1],
      })

      const result = await apiKeyService.getAvailablePermissions()

      expect((result as unknown as Record<string, unknown>).status).toBeUndefined()
      expect((result as unknown as Record<string, unknown>).message).toBeUndefined()
    })

    it('createApiKey result does not have ResponseSchema properties', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: mockApiKeyWithKey,
      })

      const result = await apiKeyService.createApiKey({ name: 'test' })

      // If the wrapper was returned, result.status would be 'success' (a string),
      // not undefined. The APIKeyWithKey interface does not have a status field.
      expect((result as unknown as Record<string, unknown>).status).toBeUndefined()
      expect((result as unknown as Record<string, unknown>).message).toBeUndefined()
    })

    it('array methods work on getUserApiKeys result', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockApiKey, mockApiKey2],
      })

      const result = await apiKeyService.getUserApiKeys()

      // All of these would fail if the ResponseSchema wrapper was returned
      expect(() => result.map((k) => k.id)).not.toThrow()
      expect(() => result.filter((k) => k.is_active)).not.toThrow()
      expect(() => result.find((k) => k.id === 'key-1')).not.toThrow()
      expect(() => result.forEach(() => {})).not.toThrow()
      expect(result.length).toBe(2)
    })

    it('array methods work on getAllApiKeys result', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockApiKey],
      })

      const result = await apiKeyService.getAllApiKeys()

      expect(() => result.map((k) => k.id)).not.toThrow()
      expect(() => result.filter((k) => k.is_active)).not.toThrow()
      expect(result.length).toBe(1)
    })

    it('array methods work on getAvailablePermissions result', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        status: 'success',
        message: 'ok',
        data: [mockPermission1, mockPermission2],
      })

      const result = await apiKeyService.getAvailablePermissions()

      expect(() => result.map((p) => p.value)).not.toThrow()
      expect(() => result.filter((p) => p.category === 'Parts')).not.toThrow()
      expect(result.length).toBe(2)
    })
  })
})
