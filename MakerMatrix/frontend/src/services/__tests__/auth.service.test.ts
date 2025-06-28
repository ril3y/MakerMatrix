import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AuthService, authService } from '../auth.service'
import { apiClient } from '../api'
import { User, LoginRequest, LoginResponse } from '@/types/auth'

// Mock dependencies
vi.mock('../api')

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

const mockApiClient = vi.mocked(apiClient)

describe('AuthService', () => {
  const mockUser: User = {
    id: '123',
    username: 'testuser',
    email: 'test@example.com',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    roles: [
      {
        id: 'role1',
        name: 'admin',
        permissions: ['parts:read', 'parts:write', 'admin:access']
      }
    ]
  }

  const mockCredentials: LoginRequest = {
    username: 'testuser',
    password: 'password123'
  }

  const mockLoginResponse: LoginResponse = {
    access_token: 'mock-jwt-token',
    token_type: 'bearer',
    user: mockUser
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
    localStorageMock.clear.mockClear()
    
    // Reset all mocks to default behavior
    localStorageMock.getItem.mockReturnValue(null)
    localStorageMock.setItem.mockReturnValue(undefined)
    localStorageMock.removeItem.mockReturnValue(undefined)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should login successfully with valid credentials', async () => {
      mockApiClient.post.mockResolvedValueOnce(mockLoginResponse)

      const result = await authService.login(mockCredentials)

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/auth/login',
        expect.any(URLSearchParams),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      )

      // Check that form data was properly encoded
      const formDataCall = mockApiClient.post.mock.calls[0][1] as URLSearchParams
      expect(formDataCall.get('username')).toBe('testuser')
      expect(formDataCall.get('password')).toBe('password123')

      expect(mockApiClient.setAuthToken).toHaveBeenCalledWith('mock-jwt-token')
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'user',
        JSON.stringify(mockUser)
      )
      expect(result).toEqual(mockLoginResponse)
    })

    it('should handle login failure', async () => {
      const errorResponse = {
        response: {
          status: 401,
          data: { detail: 'Invalid credentials' }
        }
      }
      mockApiClient.post.mockRejectedValueOnce(errorResponse)

      await expect(authService.login(mockCredentials)).rejects.toEqual(errorResponse)

      expect(mockApiClient.setAuthToken).not.toHaveBeenCalled()
      expect(localStorageMock.setItem).not.toHaveBeenCalled()
    })

    it('should not set auth token if none returned', async () => {
      const responseWithoutToken = {
        ...mockLoginResponse,
        access_token: undefined
      }
      mockApiClient.post.mockResolvedValueOnce(responseWithoutToken)

      await authService.login(mockCredentials)

      expect(mockApiClient.setAuthToken).not.toHaveBeenCalled()
      expect(localStorageMock.setItem).not.toHaveBeenCalled()
    })
  })

  describe('logout', () => {
    it('should logout successfully', async () => {
      mockApiClient.post.mockResolvedValueOnce({})

      await authService.logout()

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/logout')
      expect(mockApiClient.clearAuth).toHaveBeenCalled()
    })

    it('should clear auth even if logout request fails', async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'))

      // The method throws the API error but still clears auth due to finally block
      await expect(authService.logout()).rejects.toThrow('Network error')

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/logout')
      expect(mockApiClient.clearAuth).toHaveBeenCalled()
    })
  })

  describe('clearAuth', () => {
    it('should clear authentication state', () => {
      authService.clearAuth()

      expect(mockApiClient.clearAuth).toHaveBeenCalled()
    })
  })

  describe('getCurrentUser', () => {
    it('should fetch current user successfully', async () => {
      mockApiClient.get.mockResolvedValueOnce(mockUser)

      const result = await authService.getCurrentUser()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/users/me')
      expect(result).toEqual(mockUser)
    })

    it('should handle getCurrentUser error', async () => {
      const errorResponse = {
        response: {
          status: 401,
          data: { detail: 'Unauthorized' }
        }
      }
      mockApiClient.get.mockRejectedValueOnce(errorResponse)

      await expect(authService.getCurrentUser()).rejects.toEqual(errorResponse)
    })
  })

  describe('updatePassword', () => {
    it('should update password successfully', async () => {
      const mockResponse = {
        status: 'success',
        message: 'Password updated successfully'
      }
      mockApiClient.put.mockResolvedValueOnce(mockResponse)

      const result = await authService.updatePassword('oldpass', 'newpass')

      expect(mockApiClient.put).toHaveBeenCalledWith('/api/users/update_password', {
        current_password: 'oldpass',
        new_password: 'newpass'
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle password update error', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: { detail: 'Current password is incorrect' }
        }
      }
      mockApiClient.put.mockRejectedValueOnce(errorResponse)

      await expect(
        authService.updatePassword('wrongpass', 'newpass')
      ).rejects.toEqual(errorResponse)
    })
  })

  describe('getStoredUser', () => {
    it('should return stored user when valid JSON exists', () => {
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))

      const result = authService.getStoredUser()

      expect(localStorageMock.getItem).toHaveBeenCalledWith('user')
      expect(result).toEqual(mockUser)
    })

    it('should return null when no user stored', () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      const result = authService.getStoredUser()

      expect(result).toBeNull()
    })

    it('should return null when stored data is invalid JSON', () => {
      localStorageMock.getItem.mockReturnValueOnce('invalid-json')

      const result = authService.getStoredUser()

      expect(result).toBeNull()
    })

    it('should throw when localStorage throws error', () => {
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('localStorage error')
      })

      // The implementation doesn't catch localStorage.getItem errors
      expect(() => authService.getStoredUser()).toThrow('localStorage error')
    })
  })

  describe('isAuthenticated', () => {
    it('should return true when auth token exists', () => {
      localStorageMock.getItem.mockReturnValueOnce('some-token')

      const result = authService.isAuthenticated()

      expect(localStorageMock.getItem).toHaveBeenCalledWith('auth_token')
      expect(result).toBe(true)
    })

    it('should return false when no auth token exists', () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      const result = authService.isAuthenticated()

      expect(result).toBe(false)
    })

    it('should return false when auth token is empty string', () => {
      localStorageMock.getItem.mockReturnValueOnce('')

      const result = authService.isAuthenticated()

      expect(result).toBe(false)
    })
  })

  describe('hasRole', () => {
    it('should return true for existing role', () => {
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))
      
      const result = authService.hasRole('admin')

      expect(result).toBe(true)
    })

    it('should return false for non-existing role', () => {
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))
      
      const result = authService.hasRole('moderator')

      expect(result).toBe(false)
    })

    it('should return false when user has no roles', () => {
      const userWithoutRoles = { ...mockUser, roles: undefined }
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(userWithoutRoles))

      const result = authService.hasRole('admin')

      expect(result).toBe(false)
    })

    it('should return false when no user is stored', () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      const result = authService.hasRole('admin')

      expect(result).toBe(false)
    })
  })

  describe('hasPermission', () => {
    it('should return true for existing permission', () => {
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))
      
      const result = authService.hasPermission('parts:read')

      expect(result).toBe(true)
    })

    it('should return false for non-existing permission', () => {
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockUser))
      
      const result = authService.hasPermission('users:delete')

      expect(result).toBe(false)
    })

    it('should return false when user has no roles', () => {
      const userWithoutRoles = { ...mockUser, roles: undefined }
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(userWithoutRoles))

      const result = authService.hasPermission('parts:read')

      expect(result).toBe(false)
    })

    it('should return false when roles have no permissions', () => {
      const userWithRoleWithoutPermissions = {
        ...mockUser,
        roles: [{ id: 'role1', name: 'basic', permissions: undefined }]
      }
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(userWithRoleWithoutPermissions))

      const result = authService.hasPermission('parts:read')

      expect(result).toBe(false)
    })

    it('should return false when no user is stored', () => {
      localStorageMock.getItem.mockReturnValueOnce(null)

      const result = authService.hasPermission('parts:read')

      expect(result).toBe(false)
    })
  })

  describe('AuthService class instantiation', () => {
    it('should create a new AuthService instance', () => {
      const newAuthService = new AuthService()
      
      expect(newAuthService).toBeInstanceOf(AuthService)
      expect(newAuthService.login).toBeDefined()
      expect(newAuthService.logout).toBeDefined()
      expect(newAuthService.isAuthenticated).toBeDefined()
    })

    it('should export a singleton instance', () => {
      expect(authService).toBeInstanceOf(AuthService)
    })
  })
})