/**
 * Tests for PDF proxy utility functions.
 * 
 * Tests the getPDFProxyUrl function and related PDF proxy functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getPDFProxyUrl } from '../api'

// Mock import.meta.env
const mockEnv = vi.hoisted(() => ({
  DEV: true,
  VITE_API_URL: undefined
}))

vi.mock('virtual:env', () => ({
  default: mockEnv
}))

// Mock import.meta
Object.defineProperty(global, 'import', {
  value: {
    meta: {
      env: mockEnv
    }
  }
})

describe('PDF Proxy Utilities', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Clean up after each test
    mockEnv.DEV = true
    mockEnv.VITE_API_URL = undefined
  })

  describe('getPDFProxyUrl', () => {
    it('should generate development proxy URL with relative path', () => {
      // Set development mode
      mockEnv.DEV = true
      
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/test.pdf'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
    })

    it('should generate production proxy URL with full API URL', () => {
      // Set production mode
      mockEnv.DEV = false
      mockEnv.VITE_API_URL = 'https://api.makermatrix.com'
      
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/test.pdf'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('https://api.makermatrix.com/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
    })

    it('should use default localhost URL when VITE_API_URL is not set in production', () => {
      // Set production mode without API URL
      mockEnv.DEV = false
      mockEnv.VITE_API_URL = undefined
      
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/test.pdf'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('http://localhost:8080/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
    })

    it('should properly encode complex URLs with query parameters', () => {
      mockEnv.DEV = true
      
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/test.pdf?version=2&download=true'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
      expect(result).toContain('%3F')  // Encoded ?
      expect(result).toContain('%26')  // Encoded &
      expect(result).toContain('%3D')  // Encoded =
    })

    it('should handle URLs with special characters', () => {
      mockEnv.DEV = true
      
      const externalUrl = 'https://datasheet.lcsc.com/lcsc/TI-TLV9061IDBVR_C693210.pdf'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(externalUrl))
      expect(result).toContain('TI-TLV9061IDBVR_C693210.pdf')
    })

    it('should handle different supplier domains', () => {
      mockEnv.DEV = true
      
      const testUrls = [
        'https://lcsc.com/datasheet.pdf',
        'https://www.digikey.com/en/datasheets/test.pdf',
        'https://www.mouser.com/pdfdocs/test.pdf',
        'https://easyeda.com/datasheet/test.pdf'
      ]
      
      testUrls.forEach(url => {
        const result = getPDFProxyUrl(url)
        expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(url))
      })
    })

    it('should handle empty URL', () => {
      mockEnv.DEV = true
      
      const externalUrl = ''
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=')
    })

    it('should handle malformed URLs', () => {
      mockEnv.DEV = true
      
      const malformedUrl = 'not-a-valid-url'
      const result = getPDFProxyUrl(malformedUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(malformedUrl))
    })
  })

  describe('URL encoding edge cases', () => {
    beforeEach(() => {
      mockEnv.DEV = true
    })

    it('should handle URLs with hash fragments', () => {
      const urlWithHash = 'https://datasheet.lcsc.com/test.pdf#page=2'
      const result = getPDFProxyUrl(urlWithHash)
      
      expect(result).toContain(encodeURIComponent('#page=2'))
    })

    it('should handle URLs with authentication parameters', () => {
      const urlWithAuth = 'https://datasheet.lcsc.com/test.pdf?token=abc123&user=test'
      const result = getPDFProxyUrl(urlWithAuth)
      
      expect(result).toContain(encodeURIComponent('token=abc123'))
      expect(result).toContain(encodeURIComponent('user=test'))
    })

    it('should handle internationalized URLs', () => {
      const internationalUrl = 'https://datasheet.lcsc.com/测试.pdf'
      const result = getPDFProxyUrl(internationalUrl)
      
      expect(result).toBe('/static/proxy-pdf?url=' + encodeURIComponent(internationalUrl))
    })
  })

  describe('Environment configuration', () => {
    it('should prioritize VITE_API_URL over default in production', () => {
      mockEnv.DEV = false
      mockEnv.VITE_API_URL = 'https://custom-api.example.com'
      
      const externalUrl = 'https://test.com/file.pdf'
      const result = getPDFProxyUrl(externalUrl)
      
      expect(result).toContain('https://custom-api.example.com')
      expect(result).not.toContain('localhost')
    })

    it('should work with different API URL formats', () => {
      mockEnv.DEV = false
      
      const apiUrls = [
        'https://api.example.com',
        'https://api.example.com/',
        'http://localhost:3000',
        'https://subdomain.api.example.com:8080'
      ]
      
      apiUrls.forEach(apiUrl => {
        mockEnv.VITE_API_URL = apiUrl
        const result = getPDFProxyUrl('https://test.com/file.pdf')
        
        const expectedBase = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl
        expect(result).toContain(expectedBase + '/static/proxy-pdf')
      })
    })
  })
})