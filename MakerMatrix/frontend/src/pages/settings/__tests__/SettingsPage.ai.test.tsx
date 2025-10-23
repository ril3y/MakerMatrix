import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import SettingsPage from '../SettingsPage'
import { useTheme } from '@/contexts/ThemeContext'
import { settingsService } from '@/services/settings.service'

const toastMock = vi.hoisted(() => {
  const fn = vi.fn() as ReturnType<typeof vi.fn> & {
    success: ReturnType<typeof vi.fn>
    error: ReturnType<typeof vi.fn>
  }
  fn.success = vi.fn()
  fn.error = vi.fn()
  return fn
})

vi.mock('react-hot-toast', () => ({
  default: toastMock,
}))

vi.mock('@/contexts/ThemeContext')
const mockUseTheme = useTheme as ReturnType<typeof vi.fn>

vi.mock('@/services/settings.service', () => ({
  settingsService: {
    getAIConfig: vi.fn(),
    updateAIConfig: vi.fn(),
    testAIConnection: vi.fn(),
    getAvailableModels: vi.fn(),
    getBackupStatus: vi.fn(),
    getAvailablePrinters: vi.fn(),
  },
}))

vi.mock('@/components/ui/ThemeSelector', () => ({
  default: () => <div data-testid="theme-selector">Theme Selector Component</div>,
}))

vi.mock('@/components/import/ImportSelector', () => ({
  default: () => <div data-testid="import-selector">Import Selector</div>,
}))

vi.mock('@/components/tasks/TasksManagement', () => ({
  default: () => <div data-testid="tasks-management">Tasks Management</div>,
}))

vi.mock('@/pages/suppliers/SupplierConfigPage', () => ({
  SupplierConfigPage: () => <div data-testid="supplier-config">Supplier Config</div>,
}))

vi.mock('@/components/printer/DynamicPrinterModal', () => ({
  default: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="printer-modal">Printer Modal</div> : null,
}))

const settingsServiceMock = settingsService as unknown as {
  getAIConfig: ReturnType<typeof vi.fn>
  updateAIConfig: ReturnType<typeof vi.fn>
  testAIConnection: ReturnType<typeof vi.fn>
  getAvailableModels: ReturnType<typeof vi.fn>
  getBackupStatus: ReturnType<typeof vi.fn>
  getAvailablePrinters: ReturnType<typeof vi.fn>
}

describe('SettingsPage - AI Helper Tab', () => {
  const mockThemeContext = {
    isDarkMode: false,
    toggleDarkMode: vi.fn(),
    currentTheme: 'default',
    setTheme: vi.fn(),
    isCompactMode: false,
    toggleCompactMode: vi.fn(),
  }

  const baseAiConfig = {
    enabled: true,
    provider: 'ollama',
    api_url: 'http://localhost:11434',
    api_key: '',
    model_name: 'llama3',
    temperature: 0.7,
    max_tokens: 512,
    system_prompt: 'You are a helpful assistant',
    additional_settings: {},
  }

  const TestWrapper = ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>{children}</BrowserRouter>
  )

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTheme.mockReturnValue(mockThemeContext)

    settingsServiceMock.getAIConfig = vi.fn().mockResolvedValue(baseAiConfig)
    settingsServiceMock.getAvailableModels = vi.fn().mockResolvedValue({
      status: 'success',
      message: 'Loaded models',
      data: { models: [], provider: 'ollama' },
    })
    settingsServiceMock.testAIConnection = vi.fn()
    settingsServiceMock.updateAIConfig = vi.fn()
    settingsServiceMock.getBackupStatus = vi.fn()
    settingsServiceMock.getAvailablePrinters = vi.fn()

    toastMock.mockClear?.()
    toastMock.success.mockClear?.()
    toastMock.error.mockClear?.()
  })

  const openAiTab = async (options: { expectModelFetch?: boolean } = {}) => {
    const { expectModelFetch = true } = options
    render(<SettingsPage />, { wrapper: TestWrapper })
    const user = userEvent.setup()

    const aiTab = await screen.findByRole('button', { name: /AI Helper/i })
    await user.click(aiTab)
    await waitFor(() => expect(settingsServiceMock.getAIConfig).toHaveBeenCalled())
    if (expectModelFetch) {
      await waitFor(() => expect(settingsServiceMock.getAvailableModels).toHaveBeenCalled())
    }
  }

  it('shows an error toast when model refresh returns an error status', async () => {
    settingsServiceMock.getAvailableModels.mockResolvedValueOnce({
      status: 'error',
      message: 'Cannot connect to Ollama',
      data: { models: [], provider: 'ollama' },
    })

    await openAiTab()

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith('Cannot connect to Ollama')
    })
  })

  it('shows a warning toast when model refresh returns warnings', async () => {
    settingsServiceMock.getAvailableModels.mockResolvedValueOnce({
      status: 'warning',
      message: 'Model llama3 missing locally',
      data: { models: [], provider: 'ollama' },
    })

    await openAiTab()

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        'Model llama3 missing locally',
        expect.objectContaining({ icon: '⚠️' })
      )
    })
  })

  it('shows success toast when test connection succeeds', async () => {
    await openAiTab()

    settingsServiceMock.testAIConnection.mockResolvedValueOnce({
      status: 'success',
      message: 'Connected to Ollama',
      data: { provider: 'ollama' },
    })

    const user = userEvent.setup()
    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    await user.click(testButton)

    await waitFor(() => {
      expect(toastMock.success).toHaveBeenCalledWith('Connected to Ollama')
    })
  })

  it('shows warning toast when test connection returns warnings', async () => {
    await openAiTab()

    settingsServiceMock.testAIConnection.mockResolvedValueOnce({
      status: 'warning',
      message: 'Model unavailable',
      data: { provider: 'ollama' },
    })

    const user = userEvent.setup()
    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    await user.click(testButton)

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        'Model unavailable',
        expect.objectContaining({ icon: '⚠️' })
      )
    })
  })

  it('shows error toast when test connection fails', async () => {
    await openAiTab()

    settingsServiceMock.testAIConnection.mockResolvedValueOnce({
      status: 'error',
      message: 'Connection test failed: ECONNREFUSED',
      data: null,
    })

    const user = userEvent.setup()
    const testButton = screen.getByRole('button', { name: /Test Connection/i })
    await user.click(testButton)

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith('Connection test failed: ECONNREFUSED')
    })
  })

  it('disables model refresh when AI helper is disabled', async () => {
    settingsServiceMock.getAIConfig.mockResolvedValueOnce({
      ...baseAiConfig,
      enabled: false,
    })

    await openAiTab({ expectModelFetch: false })

    expect(settingsServiceMock.getAvailableModels).not.toHaveBeenCalled()

    const refreshButton = screen.getByRole('button', { name: /Refresh Models/i })
    expect(refreshButton).toBeDisabled()

    const user = userEvent.setup()
    await user.click(refreshButton)

    expect(settingsServiceMock.getAvailableModels).not.toHaveBeenCalled()
  })
})
