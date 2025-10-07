import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import SettingsPage from '../SettingsPage'
import { useTheme } from '@/contexts/ThemeContext'

// Mock the theme context
vi.mock('@/contexts/ThemeContext')
const mockUseTheme = useTheme as any

// Mock components
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
  default: ({ isOpen }: any) =>
    isOpen ? <div data-testid="printer-modal">Printer Modal</div> : null,
}))

// Mock services
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



// Mock react-hot-toast
const toastMock = vi.hoisted(() => {
  const fn: any = vi.fn()
  fn.success = vi.fn()
  fn.error = vi.fn()
  return fn
})

vi.mock('react-hot-toast', () => ({
  default: toastMock,
}))

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('SettingsPage - Appearance Tab', () => {
  const mockThemeContext = {
    isDarkMode: false,
    toggleDarkMode: vi.fn(),
    currentTheme: 'default',
    setTheme: vi.fn(),
    isCompactMode: false,
    toggleCompactMode: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTheme.mockReturnValue(mockThemeContext)
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Tab Navigation', () => {
    it('shows appearance tab button', () => {
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      expect(appearanceTab).toBeInTheDocument()
      expect(appearanceTab.querySelector('svg')).toBeInTheDocument() // Palette icon
    })

    it('switches to appearance tab when clicked', async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)

      expect(screen.getByText('Appearance Settings')).toBeInTheDocument()
      expect(appearanceTab).toHaveClass('bg-primary')
    })
  })

  describe('Display Mode Section', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('renders display mode section with all options', () => {
      expect(screen.getByText('Display Mode')).toBeInTheDocument()

      // Mode buttons
      expect(screen.getByText('Auto')).toBeInTheDocument()
      expect(screen.getByText('Light')).toBeInTheDocument()
      expect(screen.getByText('Dark')).toBeInTheDocument()

      // Descriptions
      expect(screen.getByText('Follow system')).toBeInTheDocument()
      expect(screen.getByText('Bright theme')).toBeInTheDocument()
      expect(screen.getByText('Easy on eyes')).toBeInTheDocument()
    })

    it('highlights current mode (light mode)', () => {
      const lightButtons = screen.getAllByText('Light')
      const lightButton = lightButtons[lightButtons.length - 1].closest('button')
      expect(lightButton).toHaveClass('border-primary', 'bg-primary-10')

      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')
      expect(darkButton).not.toHaveClass('border-primary')
    })

    it('highlights current mode (dark mode)', () => {
      mockUseTheme.mockReturnValue({ ...mockThemeContext, isDarkMode: true })

      render(<SettingsPage />, { wrapper: TestWrapper })
      const appearanceTabs = screen.getAllByRole('button', { name: /appearance/i })
      const appearanceTab = appearanceTabs[appearanceTabs.length - 1] // Get the last one (in the navigation)
      fireEvent.click(appearanceTab)

      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')
      expect(darkButton).toHaveClass('border-primary', 'bg-primary-10')

      const lightButtons = screen.getAllByText('Light')
      const lightButton = lightButtons[lightButtons.length - 1].closest('button')
      expect(lightButton).not.toHaveClass('border-primary')
    })

    it('toggles to dark mode when light mode is active', async () => {
      const user = userEvent.setup()

      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')!
      await user.click(darkButton)

      expect(mockThemeContext.toggleDarkMode).toHaveBeenCalled()
    })

    it('toggles to light mode when dark mode is active', async () => {
      const user = userEvent.setup()
      mockUseTheme.mockReturnValue({ ...mockThemeContext, isDarkMode: true })

      render(<SettingsPage />, { wrapper: TestWrapper })
      const appearanceTabs = screen.getAllByRole('button', { name: /appearance/i })
      const appearanceTab = appearanceTabs[appearanceTabs.length - 1]
      await user.click(appearanceTab)

      const lightButtons = screen.getAllByText('Light')
      const lightButton = lightButtons[lightButtons.length - 1].closest('button')!
      await user.click(lightButton)

      expect(mockThemeContext.toggleDarkMode).toHaveBeenCalled()
    })

    it('logs when auto mode is selected', async () => {
      const user = userEvent.setup()
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

      const autoButtons = screen.getAllByText('Auto')
      const autoButton = autoButtons[autoButtons.length - 1].closest('button')!
      await user.click(autoButton)

      expect(consoleSpy).toHaveBeenCalledWith('Auto mode selected')
      consoleSpy.mockRestore()
    })
  })

  describe('Color Theme Section', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('renders color theme section', () => {
      expect(screen.getByText('Color Theme')).toBeInTheDocument()
      expect(
        screen.getByText('Choose a color theme that suits your preference')
      ).toBeInTheDocument()
    })

    it('includes ThemeSelector component', () => {
      expect(screen.getByTestId('theme-selector')).toBeInTheDocument()
    })

    it('has proper section divider', () => {
      const section = screen.getByText('Color Theme').closest('.space-y-4')
      expect(section).toHaveClass('border-t', 'border-border', 'pt-6')
    })
  })

  describe('Compact Mode Section', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('renders compact mode section', () => {
      expect(screen.getByText('Compact Mode')).toBeInTheDocument()
      expect(
        screen.getByText('Reduce spacing and padding for more content density')
      ).toBeInTheDocument()
    })

    it('shows compact mode toggle with correct state', () => {
      const toggle = screen.getByRole('checkbox')
      expect(toggle).not.toBeChecked()
    })

    it('shows checked state when compact mode is enabled', () => {
      mockUseTheme.mockReturnValue({ ...mockThemeContext, isCompactMode: true })

      render(<SettingsPage />, { wrapper: TestWrapper })
      const appearanceTabs = screen.getAllByRole('button', { name: /appearance/i })
      const appearanceTab = appearanceTabs[appearanceTabs.length - 1]
      fireEvent.click(appearanceTab)

      const toggles = screen.getAllByRole('checkbox')
      const compactModeToggle = toggles[toggles.length - 1] // Get the last checkbox (compact mode)
      expect(compactModeToggle).toBeChecked()
    })

    it('toggles compact mode when clicked', async () => {
      const user = userEvent.setup()

      const toggle = screen.getByRole('checkbox')
      await user.click(toggle)

      expect(mockThemeContext.toggleCompactMode).toHaveBeenCalled()
    })

    it('has proper section divider', () => {
      const section = screen.getByText('Compact Mode').closest('.space-y-4')
      expect(section).toHaveClass('border-t', 'border-border', 'pt-6')
    })
  })

  describe('Icon Display', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('displays correct icons for display modes', () => {
      const autoButtons = screen.getAllByText('Auto')
      const autoButton = autoButtons[autoButtons.length - 1].closest('button')
      const lightButtons = screen.getAllByText('Light')
      const lightButton = lightButtons[lightButtons.length - 1].closest('button')
      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')

      expect(autoButton?.querySelector('svg')).toBeInTheDocument()
      expect(lightButton?.querySelector('svg')).toBeInTheDocument()
      expect(darkButton?.querySelector('svg')).toBeInTheDocument()
    })

    it('displays palette icon in header', () => {
      const header = screen.getByText('Appearance Settings')
      const icon = header.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('Layout and Styling', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('uses proper spacing between sections', () => {
      const container = screen.getByText('Appearance Settings').closest('.space-y-8')
      expect(container).toHaveClass('space-y-8')
    })

    it('applies hover effects to display mode buttons', () => {
      const autoButtons = screen.getAllByText('Auto')
      const autoButton = autoButtons[autoButtons.length - 1].closest('button')
      expect(autoButton).toHaveClass('hover:border-primary/30', 'hover:bg-primary/5')
    })

    it('uses grid layout for display mode buttons', () => {
      const buttonContainer = screen.getByText('Auto').closest('.grid')
      expect(buttonContainer).toHaveClass('grid', 'grid-cols-1', 'sm:grid-cols-3', 'gap-4')
    })

    it('applies proper padding to mode buttons', () => {
      const autoButtons = screen.getAllByText('Auto')
      const autoButton = autoButtons[autoButtons.length - 1].closest('button')
      expect(autoButton).toHaveClass('p-4')
    })
  })

  describe('Accessibility', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      render(<SettingsPage />, { wrapper: TestWrapper })

      const appearanceTab = screen.getByRole('button', { name: /appearance/i })
      await user.click(appearanceTab)
    })

    it('has proper heading hierarchy', () => {
      const mainHeading = screen.getByRole('heading', { level: 3, name: /appearance settings/i })
      expect(mainHeading).toBeInTheDocument()

      const subHeadings = screen.getAllByRole('heading', { level: 4 })
      expect(subHeadings).toHaveLength(3) // Display Mode, Color Theme, Compact Mode
    })

    it('uses semantic HTML for toggle', () => {
      const toggle = screen.getByRole('checkbox')
      expect(toggle).toHaveAttribute('type', 'checkbox')
      expect(toggle).toHaveClass('sr-only') // Screen reader only
    })

    it('provides descriptive text for all options', () => {
      expect(screen.getByText('Follow system')).toBeInTheDocument()
      expect(screen.getByText('Bright theme')).toBeInTheDocument()
      expect(screen.getByText('Easy on eyes')).toBeInTheDocument()
      expect(
        screen.getByText('Choose a color theme that suits your preference')
      ).toBeInTheDocument()
      expect(
        screen.getByText('Reduce spacing and padding for more content density')
      ).toBeInTheDocument()
    })

    it('has keyboard accessible buttons', () => {
      const buttons = screen
        .getAllByRole('button')
        .filter(
          (btn) =>
            btn.textContent?.includes('Auto') ||
            btn.textContent?.includes('Light') ||
            btn.textContent?.includes('Dark')
        )

      buttons.forEach((button) => {
        expect(button.tagName.toLowerCase()).toBe('button')
        expect(button).not.toHaveAttribute('disabled')
      })
    })
  })

  describe('Integration with Theme System', () => {
    it('correctly reads theme state from context', () => {
      const customTheme = {
        isDarkMode: true,
        toggleDarkMode: vi.fn(),
        currentTheme: 'purple',
        setTheme: vi.fn(),
        isCompactMode: true,
        toggleCompactMode: vi.fn(),
      }

      mockUseTheme.mockReturnValue(customTheme)

      render(<SettingsPage />, { wrapper: TestWrapper })
      const appearanceTabs = screen.getAllByRole('button', { name: /appearance/i })
      const appearanceTab = appearanceTabs[appearanceTabs.length - 1]
      fireEvent.click(appearanceTab)

      // Dark mode should be selected
      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')
      expect(darkButton).toHaveClass('border-primary')

      // Compact mode should be checked
      const toggle = screen.getByRole('checkbox')
      expect(toggle).toBeChecked()
    })

    it('calls theme functions with correct parameters', async () => {
      const user = userEvent.setup()
      const customTheme = {
        ...mockThemeContext,
        isDarkMode: false,
      }

      mockUseTheme.mockReturnValue(customTheme)

      render(<SettingsPage />, { wrapper: TestWrapper })
      const appearanceTabs = screen.getAllByRole('button', { name: /appearance/i })
      const appearanceTab = appearanceTabs[appearanceTabs.length - 1]
      await user.click(appearanceTab)

      // Click dark mode
      const darkButtons = screen.getAllByText('Dark')
      const darkButton = darkButtons[darkButtons.length - 1].closest('button')!
      await user.click(darkButton)

      expect(customTheme.toggleDarkMode).toHaveBeenCalledTimes(1)

      // Toggle compact mode
      const toggle = screen.getByRole('checkbox')
      await user.click(toggle)

      expect(customTheme.toggleCompactMode).toHaveBeenCalledTimes(1)
    })
  })
})
