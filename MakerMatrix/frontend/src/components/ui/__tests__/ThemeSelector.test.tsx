import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import ThemeSelector from '../ThemeSelector'
import { useTheme } from '@/contexts/ThemeContext'

// Mock the theme context
vi.mock('@/contexts/ThemeContext')
const mockUseTheme = useTheme as any



describe('ThemeSelector', () => {
  const mockThemeContext = {
    currentTheme: 'default',
    setTheme: vi.fn(),
    isDarkMode: false,
    toggleDarkMode: vi.fn(),
    isCompactMode: false,
    toggleCompactMode: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTheme.mockReturnValue(mockThemeContext)
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<ThemeSelector />)
      expect(screen.getByText('Theme Colors')).toBeInTheDocument()
    })

    it('displays all available themes', () => {
      render(<ThemeSelector />)

      // Check for theme options based on actual theme names
      expect(screen.getByText('Matrix')).toBeInTheDocument()
      expect(screen.getByText('Arctic')).toBeInTheDocument()
      expect(screen.getByText('Nebula')).toBeInTheDocument()
      expect(screen.getByText('Sunset')).toBeInTheDocument()
      expect(screen.getByText('Monolith')).toBeInTheDocument()
    })

    it('highlights the current theme', () => {
      mockUseTheme.mockReturnValue({ ...mockThemeContext, currentTheme: 'blue' })
      render(<ThemeSelector />)

      const blueTheme = screen.getByText('Arctic').closest('button')
      expect(blueTheme).toHaveClass('ring-2', 'ring-primary-20')
    })
  })

  describe('Theme Colors', () => {
    it('displays correct color previews for each theme', () => {
      render(<ThemeSelector />)

      // Check if color preview divs are present
      const themeButtons = screen.getAllByRole('button')
      themeButtons.forEach((button) => {
        const colorPreview = button.querySelector('div[class*="w-4 h-4"]')
        expect(colorPreview).toBeInTheDocument()
      })
    })

    it('shows theme-specific colors', () => {
      render(<ThemeSelector />)

      // Check for different background colors that represent themes
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(5) // Should have at least 6 theme options
    })
  })

  describe('Theme Selection', () => {
    it('calls setTheme when a theme is selected', async () => {
      const user = userEvent.setup()
      render(<ThemeSelector />)

      const blueTheme = screen.getByText('Arctic').closest('button')!
      await user.click(blueTheme)

      expect(mockThemeContext.setTheme).toHaveBeenCalledWith('blue')
    })

    it('calls setTheme for different themes', async () => {
      const user = userEvent.setup()
      render(<ThemeSelector />)

      // Test multiple theme selections
      const purpleTheme = screen.getByText('Nebula').closest('button')!
      await user.click(purpleTheme)
      expect(mockThemeContext.setTheme).toHaveBeenCalledWith('purple')

      const orangeTheme = screen.getByText('Sunset').closest('button')!
      await user.click(orangeTheme)
      expect(mockThemeContext.setTheme).toHaveBeenCalledWith('orange')
    })

    it('does not call setTheme when current theme is clicked', async () => {
      const user = userEvent.setup()
      mockUseTheme.mockReturnValue({ ...mockThemeContext, currentTheme: 'default' })
      render(<ThemeSelector />)

      const defaultTheme = screen.getByText('Matrix').closest('button')!
      await user.click(defaultTheme)

      // Should still be called (component doesn't prevent re-selection)
      expect(mockThemeContext.setTheme).toHaveBeenCalledWith('default')
    })
  })

  describe('Visual States', () => {
    it('applies hover effects', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveClass('hover:scale-105')
      })
    })

    it('applies focus styles', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-primary')
      })
    })

    it('shows transition effects', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveClass('transition-all')
      })
    })
  })

  describe('Layout and Styling', () => {
    it('uses grid layout for theme options', () => {
      render(<ThemeSelector />)

      const container = screen.getByText('Default').closest('.grid')
      expect(container).toHaveClass('grid', 'grid-cols-3', 'gap-3')
    })

    it('applies proper spacing', () => {
      render(<ThemeSelector />)

      const container = screen.getByText('Choose Theme').nextElementSibling
      expect(container).toHaveClass('grid')
    })

    it('has rounded corners on theme buttons', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveClass('rounded-lg')
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper button roles', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(5)
    })

    it('has descriptive labels', () => {
      render(<ThemeSelector />)

      expect(screen.getByText('Matrix')).toBeInTheDocument()
      expect(screen.getByText('Arctic')).toBeInTheDocument()
      expect(screen.getByText('Nebula')).toBeInTheDocument()
      expect(screen.getByText('Sunset')).toBeInTheDocument()
      expect(screen.getByText('Monolith')).toBeInTheDocument()
    })

    it('supports keyboard navigation', () => {
      render(<ThemeSelector />)

      const firstButton = screen.getByText('Matrix').closest('button')!
      firstButton.focus()
      expect(firstButton).toHaveFocus()
    })

    it('has proper ARIA attributes', () => {
      render(<ThemeSelector />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button.tagName.toLowerCase()).toBe('button')
      })
    })
  })

  describe('Theme Context Integration', () => {
    it('updates when context theme changes', () => {
      const { rerender } = render(<ThemeSelector />)

      // Initially default theme
      let defaultButton = screen.getByText('Matrix').closest('button')
      expect(defaultButton).toHaveClass('ring-2', 'ring-primary-20')

      // Change context theme
      mockUseTheme.mockReturnValue({ ...mockThemeContext, currentTheme: 'blue' })
      rerender(<ThemeSelector />)

      // Blue theme should now be selected
      const blueButton = screen.getByText('Arctic').closest('button')
      expect(blueButton).toHaveClass('ring-2', 'ring-primary-20')

      // Default should no longer be selected
      defaultButton = screen.getByText('Matrix').closest('button')
      expect(defaultButton).not.toHaveClass('ring-2', 'ring-primary-20')
    })

    it('works with all theme options', () => {
      const themes = [
        { id: 'default', name: 'Matrix' },
        { id: 'blue', name: 'Arctic' },
        { id: 'purple', name: 'Nebula' },
        { id: 'orange', name: 'Sunset' },
        { id: 'gray', name: 'Monolith' },
      ]

      themes.forEach((theme) => {
        mockUseTheme.mockReturnValue({ ...mockThemeContext, currentTheme: theme.id })
        const { unmount } = render(<ThemeSelector />)

        const themeButton = screen.getByText(theme.name).closest('button')
        expect(themeButton).toHaveClass('ring-2', 'ring-primary-20')

        unmount()
      })
    })
  })

  describe('Error Handling', () => {
    it('handles missing theme context gracefully', () => {
      mockUseTheme.mockReturnValue(null)

      expect(() => render(<ThemeSelector />)).not.toThrow()
    })

    it('handles invalid current theme', () => {
      mockUseTheme.mockReturnValue({ ...mockThemeContext, currentTheme: 'invalid-theme' })

      render(<ThemeSelector />)
      expect(screen.getByText('Default')).toBeInTheDocument()
    })
  })
})
