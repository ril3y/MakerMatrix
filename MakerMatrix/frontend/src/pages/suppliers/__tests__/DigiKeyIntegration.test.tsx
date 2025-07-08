/**
 * DigiKey Integration Tests
 * 
 * Tests that validate DigiKey frontend integration with the backend API.
 * These tests complement the backend DigiKey tests to ensure full functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../../__tests__/utils/render'
import { supplierService } from '../../../services/supplier.service'
import { EditSupplierModal } from '../EditSupplierModal'
import { DigiKeyConfigForm } from '../DigiKeyConfigForm'

// Mock the supplier service
vi.mock('../../../services/supplier.service', () => ({
  supplierService: {
    getSuppliers: vi.fn(),
    testConnection: vi.fn(),
    getCredentialStatus: vi.fn(),
    saveCredentials: vi.fn(),
    updateSupplier: vi.fn(),
  }
}))

describe('DigiKey Frontend Integration', () => {
  const mockDigiKeySupplier = {
    id: '1',
    supplier_name: 'digikey',
    display_name: 'DigiKey Electronics',
    description: 'Global electronic components distributor',
    api_type: 'rest' as const,
    base_url: 'https://api.digikey.com',
    enabled: true,
    capabilities: ['get_part_details', 'fetch_datasheet', 'fetch_pricing', 'import_orders'],
    custom_headers: {},
    custom_parameters: {},
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    timeout_seconds: 30,
    max_retries: 3,
    retry_backoff: 1
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('DigiKey Configuration Form', () => {
    it('renders DigiKey-specific configuration fields', () => {
      const mockConfig = {
        supplier_name: 'digikey',
        display_name: 'DigiKey Electronics',
        oauth_callback_url: 'https://localhost:8443/api/suppliers/digikey/oauth/callback',
        storage_path: './digikey_tokens'
      }
      
      const onConfigChange = vi.fn()
      
      render(
        <DigiKeyConfigForm 
          config={mockConfig} 
          onConfigChange={onConfigChange} 
          errors={[]} 
        />
      )

      // Check for DigiKey-specific instructions
      expect(screen.getByText(/DigiKey API Setup Instructions/)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /developer.digikey.com/ })).toBeInTheDocument()

      // Check for OAuth callback URL field
      expect(screen.getByDisplayValue(/\/api\/suppliers\/digikey\/oauth\/callback/)).toBeInTheDocument()
      
      // Check for token storage path field
      expect(screen.getByDisplayValue('./digikey_tokens')).toBeInTheDocument()

      // Check for environment mode selector
      expect(screen.getByText('Environment Mode')).toBeInTheDocument()
      expect(screen.getByText(/Sandbox.*Testing/)).toBeInTheDocument()
      expect(screen.getByText(/Production.*api.digikey.com/)).toBeInTheDocument()
    })

    it('shows production warning when production mode is selected', () => {
      const mockConfig = {
        supplier_name: 'digikey',
        sandbox_mode: false // Production mode
      }
      
      render(
        <DigiKeyConfigForm 
          config={mockConfig} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      expect(screen.getByText(/Production Mode/)).toBeInTheDocument()
      expect(screen.getByText(/live DigiKey API/)).toBeInTheDocument()
    })

    it('calls onConfigChange when OAuth callback URL is modified', () => {
      const onConfigChange = vi.fn()
      const mockConfig = { supplier_name: 'digikey' }
      
      render(
        <DigiKeyConfigForm 
          config={mockConfig} 
          onConfigChange={onConfigChange} 
          errors={[]} 
        />
      )

      const callbackInput = screen.getByDisplayValue(/oauth\/callback/)
      fireEvent.change(callbackInput, { 
        target: { value: 'https://example.com/custom/callback' } 
      })

      expect(onConfigChange).toHaveBeenCalledWith('oauth_callback_url', 'https://example.com/custom/callback')
    })
  })

  describe('DigiKey Connection Testing', () => {
    it('performs connection test with DigiKey credentials', async () => {
      const mockTestResult = {
        supplier_name: 'digikey',
        success: true,
        test_duration_seconds: 1.5,
        tested_at: new Date().toISOString(),
        message: 'OAuth authentication required for full DigiKey access'
      }

      vi.mocked(supplierService.testConnection).mockResolvedValue(mockTestResult)
      vi.mocked(supplierService.getCredentialStatus).mockResolvedValue({
        has_credentials: true,
        credential_count: 2,
        required_credentials: ['client_id', 'client_secret'],
        missing_credentials: []
      })

      const onClose = vi.fn()
      const onSuccess = vi.fn()

      render(
        <EditSupplierModal 
          supplier={mockDigiKeySupplier} 
          onClose={onClose} 
          onSuccess={onSuccess} 
        />
      )

      // Wait for component to load capabilities
      await waitFor(() => {
        expect(screen.getByText('DigiKey Electronics')).toBeInTheDocument()
      })

      // Find and click test connection button
      const testButton = screen.getByRole('button', { name: /test connection/i })
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(supplierService.testConnection).toHaveBeenCalledWith('digikey', {})
      })

      // Check for success message
      await waitFor(() => {
        expect(screen.getByText(/OAuth authentication required/)).toBeInTheDocument()
      })
    })

    it('handles DigiKey connection test failures', async () => {
      const mockTestResult = {
        supplier_name: 'digikey',
        success: false,
        test_duration_seconds: 0.5,
        tested_at: new Date().toISOString(),
        error_message: 'DigiKey not configured - missing client_id and client_secret'
      }

      vi.mocked(supplierService.testConnection).mockResolvedValue(mockTestResult)
      vi.mocked(supplierService.getCredentialStatus).mockResolvedValue({
        has_credentials: false,
        credential_count: 0,
        required_credentials: ['client_id', 'client_secret'],
        missing_credentials: ['client_id', 'client_secret']
      })

      const onClose = vi.fn()
      const onSuccess = vi.fn()

      render(
        <EditSupplierModal 
          supplier={mockDigiKeySupplier} 
          onClose={onClose} 
          onSuccess={onSuccess} 
        />
      )

      await waitFor(() => {
        expect(screen.getByText('DigiKey Electronics')).toBeInTheDocument()
      })

      const testButton = screen.getByRole('button', { name: /test connection/i })
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(supplierService.testConnection).toHaveBeenCalledWith('digikey', {})
      })

      // Check for error message
      await waitFor(() => {
        expect(screen.getByText(/missing client_id and client_secret/)).toBeInTheDocument()
      })
    })

    it('shows OAuth setup instructions for DigiKey', async () => {
      const mockTestResult = {
        supplier_name: 'digikey',
        success: true,
        test_duration_seconds: 1.0,
        tested_at: new Date().toISOString(),
        message: 'API reachable. OAuth setup required for authentication.',
        details: {
          api_reachable: true,
          oauth_setup_required: true,
          callback_url: 'https://localhost:8443/api/suppliers/digikey/oauth/callback'
        }
      }

      vi.mocked(supplierService.testConnection).mockResolvedValue(mockTestResult)

      const onClose = vi.fn()
      const onSuccess = vi.fn()

      render(
        <EditSupplierModal 
          supplier={mockDigiKeySupplier} 
          onClose={onClose} 
          onSuccess={onSuccess} 
        />
      )

      await waitFor(() => {
        expect(screen.getByText('DigiKey Electronics')).toBeInTheDocument()
      })

      const testButton = screen.getByRole('button', { name: /test connection/i })
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(screen.getByText(/OAuth setup required/)).toBeInTheDocument()
      })
    })
  })

  describe('DigiKey OAuth Flow Integration', () => {
    it('displays correct OAuth callback URL for DigiKey', () => {
      const mockConfig = {
        supplier_name: 'digikey',
        oauth_callback_url: 'https://localhost:8443/api/suppliers/digikey/oauth/callback'
      }
      
      render(
        <DigiKeyConfigForm 
          config={mockConfig} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      // Should show the auto-detected callback URL
      expect(screen.getByDisplayValue(/localhost:8443.*digikey.*oauth.*callback/)).toBeInTheDocument()
    })

    it('warns about exact callback URL match requirement', () => {
      render(
        <DigiKeyConfigForm 
          config={{}} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      // Should show warning about exact URL match in tooltip
      const helpIcon = screen.getAllByRole('generic').find(el => 
        el.className.includes('group-hover:opacity-100')
      )
      expect(helpIcon).toBeInTheDocument()
    })
  })

  describe('DigiKey Capabilities Display', () => {
    it('shows all DigiKey capabilities as enabled', () => {
      render(
        <DigiKeyConfigForm 
          config={{}} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      // Check for DigiKey-specific capabilities
      expect(screen.getByText('Datasheet Download')).toBeInTheDocument()
      expect(screen.getByText('Image Download')).toBeInTheDocument()
      expect(screen.getByText('Pricing Information')).toBeInTheDocument()
      expect(screen.getByText('Stock Information')).toBeInTheDocument()
      expect(screen.getByText('Technical Specifications')).toBeInTheDocument()

      // All capabilities should be checked and disabled (auto-configured)
      const checkboxes = screen.getAllByRole('checkbox')
      checkboxes.forEach(checkbox => {
        expect(checkbox).toBeChecked()
        expect(checkbox).toBeDisabled()
      })
    })

    it('explains that capabilities are auto-configured', () => {
      render(
        <DigiKeyConfigForm 
          config={{}} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      expect(screen.getByText(/automatically configured.*API features/)).toBeInTheDocument()
    })
  })

  describe('DigiKey Credential Management', () => {
    it('shows appropriate credential requirements', () => {
      render(
        <DigiKeyConfigForm 
          config={{}} 
          onConfigChange={vi.fn()} 
          errors={[]} 
        />
      )

      // Should show next step instructions
      expect(screen.getByText('Next Step: Add Credentials')).toBeInTheDocument()
      expect(screen.getByText(/Client ID and Client Secret/)).toBeInTheDocument()
      expect(screen.getByText(/Manage Credentials.*button/)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays connection timeout errors appropriately', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Connection timeout: DigiKey API not reachable'
          }
        }
      }

      vi.mocked(supplierService.testConnection).mockRejectedValue(mockError)

      const onClose = vi.fn()
      const onSuccess = vi.fn()

      render(
        <EditSupplierModal 
          supplier={mockDigiKeySupplier} 
          onClose={onClose} 
          onSuccess={onSuccess} 
        />
      )

      await waitFor(() => {
        expect(screen.getByText('DigiKey Electronics')).toBeInTheDocument()
      })

      const testButton = screen.getByRole('button', { name: /test connection/i })
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(screen.getByText(/Connection timeout.*not reachable/)).toBeInTheDocument()
      })
    })

    it('handles missing DigiKey library errors', async () => {
      const mockTestResult = {
        supplier_name: 'digikey',
        success: false,
        test_duration_seconds: 0,
        tested_at: new Date().toISOString(),
        error_message: 'DigiKey API library not available. Install with: pip install digikey-api'
      }

      vi.mocked(supplierService.testConnection).mockResolvedValue(mockTestResult)

      const onClose = vi.fn()
      const onSuccess = vi.fn()

      render(
        <EditSupplierModal 
          supplier={mockDigiKeySupplier} 
          onClose={onClose} 
          onSuccess={onSuccess} 
        />
      )

      await waitFor(() => {
        expect(screen.getByText('DigiKey Electronics')).toBeInTheDocument()
      })

      const testButton = screen.getByRole('button', { name: /test connection/i })
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(screen.getByText(/library not available.*pip install/)).toBeInTheDocument()
      })
    })
  })
})