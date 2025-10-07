import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import PartsPage from '../PartsPage'
import { partsService } from '@/services/parts.service'

// Mock the parts service
vi.mock('@/services/parts.service')
const mockPartsService = partsService as any

// Mock react-router-dom navigation
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock components
vi.mock('@/components/parts/AddPartModal', () => ({
  default: ({ isOpen, onClose, onSuccess }: any) =>
    isOpen ? (
      <div data-testid="add-part-modal">
        <button
          onClick={() => {
            onSuccess()
            onClose()
          }}
        >
          Add Part
        </button>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}))

vi.mock('@/components/ui/LoadingScreen', () => ({
  default: () => <div data-testid="loading-screen">Loading...</div>,
}))

vi.mock('@/components/parts/PartImage', () => ({
  default: ({ partName }: any) => <img alt={`Part image: ${partName}`} data-testid="part-image" />,
}))

// Mock data
const mockParts = [
  {
    id: '1',
    name: 'Arduino Uno R3',
    part_number: 'ARD-UNO-R3',
    quantity: 10,
    minimum_quantity: 5,
    supplier: 'Arduino',
    location: { id: 'loc1', name: 'Shelf A1' },
    categories: [{ id: 'cat1', name: 'Microcontrollers' }],
    image_url: 'http://example.com/arduino.jpg',
    additional_properties: {
      description: 'Arduino Uno R3 microcontroller board',
    },
  },
  {
    id: '2',
    name: 'Resistor 10K Ohm',
    part_number: 'RES-10K',
    quantity: 100,
    minimum_quantity: 20,
    supplier: 'Vishay',
    location: { id: 'loc2', name: 'Drawer B2' },
    categories: [{ id: 'cat2', name: 'Resistors' }],
    image_url: null,
    additional_properties: {
      description: '10K Ohm 1/4W resistor',
    },
  },
]

const mockApiResponse = {
  data: mockParts,
  total_parts: 2,
  page: 1,
  page_size: 20,
}

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('PartsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPartsService.getAllParts.mockResolvedValue(mockApiResponse)
    mockPartsService.searchPartsText.mockResolvedValue(mockApiResponse)
    mockPartsService.getPartSuggestions.mockResolvedValue(['Arduino Uno R3', 'Arduino Nano'])
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Basic Rendering', () => {
    it('renders page header and title correctly', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      expect(screen.getByText('Parts Inventory')).toBeInTheDocument()
      expect(screen.getByText('Manage your parts inventory')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /add part/i })).toBeInTheDocument()
    })

    it('shows loading screen initially', () => {
      render(<PartsPage />, { wrapper: TestWrapper })
      expect(screen.getByTestId('loading-screen')).toBeInTheDocument()
    })

    it('displays parts list after loading', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
        expect(screen.getByText('Resistor 10K Ohm')).toBeInTheDocument()
      })

      expect(mockPartsService.getAllParts).toHaveBeenCalledWith(1, 20)
    })

    it('shows empty state when no parts found', async () => {
      mockPartsService.getAllParts.mockResolvedValue({
        data: [],
        total_parts: 0,
        page: 1,
        page_size: 20,
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('No Parts Found')).toBeInTheDocument()
        expect(
          screen.getByText('Start by adding your first part to the inventory.')
        ).toBeInTheDocument()
      })
    })
  })

  describe('Search Functionality', () => {
    it('renders search input and controls', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument()
      })
    })

    it('performs search when form is submitted', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(searchInput, 'Arduino')
      await user.click(searchButton)

      await waitFor(() => {
        expect(mockPartsService.searchPartsText).toHaveBeenCalledWith('Arduino', 1, 20)
      })
    })

    it('shows search suggestions when typing', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)

      // Type more than 3 characters to trigger suggestions
      await user.type(searchInput, 'Ardu')

      await waitFor(() => {
        expect(mockPartsService.getPartSuggestions).toHaveBeenCalledWith('Ardu', 8)
      })

      // Wait for suggestions to appear
      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
        expect(screen.getByText('Arduino Nano')).toBeInTheDocument()
      })
    })

    it('handles suggestion clicks', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      await user.type(searchInput, 'Ardu')

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Arduino Uno R3'))

      await waitFor(() => {
        expect(mockPartsService.searchPartsText).toHaveBeenCalledWith('Arduino Uno R3', 1, 20)
      })
    })

    it('clears search when clear button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      await user.type(searchInput, 'Arduino')

      // Clear button should appear
      const clearButton = screen.getByRole('button', { name: /clear/i })
      await user.click(clearButton)

      expect(searchInput).toHaveValue('')
      await waitFor(() => {
        expect(mockPartsService.getAllParts).toHaveBeenCalledWith(1, '')
      })
    })

    it('shows search status when searching', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(searchInput, 'Arduino')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Found 2 results for "Arduino"')).toBeInTheDocument()
      })
    })
  })

  describe('Parts Table', () => {
    it('displays all part information correctly', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        // Check part names
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
        expect(screen.getByText('Resistor 10K Ohm')).toBeInTheDocument()

        // Check part numbers
        expect(screen.getByText('ARD-UNO-R3')).toBeInTheDocument()
        expect(screen.getByText('RES-10K')).toBeInTheDocument()

        // Check quantities
        expect(screen.getByText('10')).toBeInTheDocument()
        expect(screen.getByText('100')).toBeInTheDocument()

        // Check locations
        expect(screen.getByText('Shelf A1')).toBeInTheDocument()
        expect(screen.getByText('Drawer B2')).toBeInTheDocument()

        // Check categories
        expect(screen.getByText('Microcontrollers')).toBeInTheDocument()
        expect(screen.getByText('Resistors')).toBeInTheDocument()

        // Check suppliers
        expect(screen.getByText('Arduino')).toBeInTheDocument()
        expect(screen.getByText('Vishay')).toBeInTheDocument()
      })
    })

    it('highlights low quantity parts', async () => {
      const lowQuantityPart = {
        ...mockParts[0],
        quantity: 3,
        minimum_quantity: 5,
      }

      mockPartsService.getAllParts.mockResolvedValue({
        data: [lowQuantityPart],
        total_parts: 1,
        page: 1,
        page_size: 20,
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        const quantityCell = screen.getByText('3')
        expect(quantityCell).toHaveClass('text-red-400')
      })
    })

    it('navigates to part details when view button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getAllByText('View')).toHaveLength(2)
      })

      const viewButtons = screen.getAllByText('View')
      await user.click(viewButtons[0])

      expect(mockNavigate).toHaveBeenCalledWith('/parts/1')
    })

    it('displays part images correctly', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        const images = screen.getAllByTestId('part-image')
        expect(images).toHaveLength(2)
      })
    })
  })

  describe('Pagination', () => {
    it('shows pagination when there are multiple pages', async () => {
      mockPartsService.getAllParts.mockResolvedValue({
        data: mockParts,
        total_parts: 50,
        page: 1,
        page_size: 20,
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Showing 1 to 20 of 50 parts')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()
        expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled()
      })
    })

    it('navigates to next page when next button is clicked', async () => {
      const user = userEvent.setup()
      mockPartsService.getAllParts.mockResolvedValue({
        data: mockParts,
        total_parts: 50,
        page: 1,
        page_size: 20,
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
      })

      const nextButton = screen.getByRole('button', { name: /next/i })
      await user.click(nextButton)

      await waitFor(() => {
        expect(mockPartsService.getAllParts).toHaveBeenCalledWith(2, '')
      })
    })

    it('navigates to specific page when page number is clicked', async () => {
      const user = userEvent.setup()
      mockPartsService.getAllParts.mockResolvedValue({
        data: mockParts,
        total_parts: 100,
        page: 1,
        page_size: 20,
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument()
      })

      const page3Button = screen.getByText('3')
      await user.click(page3Button)

      await waitFor(() => {
        expect(mockPartsService.getAllParts).toHaveBeenCalledWith(3, '')
      })
    })
  })

  describe('Add Part Modal', () => {
    it('opens add part modal when add button is clicked', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      const addButton = screen.getByRole('button', { name: /add part/i })
      await user.click(addButton)

      expect(screen.getByTestId('add-part-modal')).toBeInTheDocument()
    })

    it('reloads parts list when part is added successfully', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      const addButton = screen.getByRole('button', { name: /add part/i })
      await user.click(addButton)

      const modalAddButton = screen.getByRole('button', { name: 'Add Part' })
      await user.click(modalAddButton)

      // Should reload parts after successful addition
      await waitFor(() => {
        expect(mockPartsService.getAllParts).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when parts loading fails', async () => {
      const errorMessage = 'Failed to load parts'
      mockPartsService.getAllParts.mockRejectedValue({
        response: { data: { error: errorMessage } },
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    it('dismisses error message when dismiss button is clicked', async () => {
      const user = userEvent.setup()
      const errorMessage = 'Failed to load parts'
      mockPartsService.getAllParts.mockRejectedValue({
        response: { data: { error: errorMessage } },
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })

      const dismissButton = screen.getByText('Dismiss')
      await user.click(dismissButton)

      expect(screen.queryByText(errorMessage)).not.toBeInTheDocument()
    })

    it('handles search errors gracefully', async () => {
      const user = userEvent.setup()
      mockPartsService.searchPartsText.mockRejectedValue({
        response: { data: { error: 'Search failed' } },
      })

      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(searchInput, 'Arduino')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Search failed')).toBeInTheDocument()
      })
    })
  })

  describe('Keyboard Navigation', () => {
    it('handles keyboard navigation in search suggestions', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search parts/i)).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      await user.type(searchInput, 'Ardu')

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      // Test arrow down navigation
      await user.keyboard('{ArrowDown}')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(mockPartsService.searchPartsText).toHaveBeenCalledWith('Arduino Uno R3', 1, 20)
      })
    })

    it('closes suggestions on escape key', async () => {
      const user = userEvent.setup()
      render(<PartsPage />, { wrapper: TestWrapper })

      const searchInput = screen.getByPlaceholderText(/search parts/i)
      await user.type(searchInput, 'Ardu')

      await waitFor(() => {
        expect(screen.getByText('Arduino Uno R3')).toBeInTheDocument()
      })

      await user.keyboard('{Escape}')

      await waitFor(() => {
        expect(screen.queryByText('Arduino Uno R3')).not.toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add part/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
        expect(screen.getByRole('textbox')).toBeInTheDocument()
      })
    })

    it('supports screen reader navigation', async () => {
      render(<PartsPage />, { wrapper: TestWrapper })

      await waitFor(() => {
        const table = screen.getByRole('table')
        expect(table).toBeInTheDocument()

        const columnHeaders = screen.getAllByRole('columnheader')
        expect(columnHeaders).toHaveLength(8) // Image, Name, Part Number, Quantity, Location, Categories, Supplier, Actions
      })
    })
  })
})
