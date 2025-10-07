import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

// Mock components (you'll need to import the actual components)
import PartsPage from '../../pages/parts/PartsPage'
import LocationsPage from '../../pages/locations/LocationsPage'
import CategoriesPage from '../../pages/categories/CategoriesPage'

// Mock services
vi.mock('../../services/parts.service')
vi.mock('../../services/locations.service')
vi.mock('../../services/categories.service')
vi.mock('../../store/authStore', () => ({
  authStore: {
    getState: () => ({
      user: { id: 'test-user', username: 'testuser' },
      token: 'test-token',
    }),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
      </QueryClientProvider>
    </BrowserRouter>
  )
}

describe('CRUD Flow Integration Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Parts CRUD Flow', () => {
    it('should complete full CRUD cycle for parts', async () => {
      const { partService } = await import('../../services/parts.service')

      // Mock service responses
      vi.mocked(partService.getAllParts).mockResolvedValueOnce({
        parts: [],
        total: 0,
        page: 1,
        pageSize: 10,
      })

      const mockPart = {
        id: 'test-id',
        part_name: 'Test Resistor',
        part_number: 'RES-001',
        quantity: 100,
        description: 'Test resistor',
      }

      vi.mocked(partService.addPart).mockResolvedValueOnce(mockPart)
      vi.mocked(partService.getAllParts).mockResolvedValueOnce({
        parts: [mockPart],
        total: 1,
        page: 1,
        pageSize: 10,
      })

      render(<PartsPage />, { wrapper: createWrapper() })

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText(/parts inventory/i)).toBeInTheDocument()
      })

      // Click add button
      const addButton = screen.getByRole('button', { name: /add part/i })
      await user.click(addButton)

      // Fill form
      await waitFor(() => {
        expect(screen.getByLabelText(/part name/i)).toBeInTheDocument()
      })

      await user.type(screen.getByLabelText(/part name/i), 'Test Resistor')
      await user.type(screen.getByLabelText(/part number/i), 'RES-001')
      await user.type(screen.getByLabelText(/quantity/i), '100')
      await user.type(screen.getByLabelText(/description/i), 'Test resistor')

      // Submit form
      const submitButton = screen.getByRole('button', { name: /save|add/i })
      await user.click(submitButton)

      // Verify part appears in list
      await waitFor(() => {
        expect(screen.getByText('Test Resistor')).toBeInTheDocument()
        expect(screen.getByText('RES-001')).toBeInTheDocument()
      })

      // Test edit
      vi.mocked(partService.updatePart).mockResolvedValueOnce({
        ...mockPart,
        quantity: 150,
      })

      const editButton = screen.getByRole('button', { name: /edit/i })
      await user.click(editButton)

      const quantityInput = screen.getByLabelText(/quantity/i)
      await user.clear(quantityInput)
      await user.type(quantityInput, '150')

      const updateButton = screen.getByRole('button', { name: /update|save/i })
      await user.click(updateButton)

      // Verify update
      await waitFor(() => {
        expect(partService.updatePart).toHaveBeenCalledWith(
          'test-id',
          expect.objectContaining({
            quantity: 150,
          })
        )
      })

      // Test delete
      vi.mocked(partService.deletePart).mockResolvedValueOnce({ success: true })
      vi.mocked(partService.getAllParts).mockResolvedValueOnce({
        parts: [],
        total: 0,
        page: 1,
        pageSize: 10,
      })

      const deleteButton = screen.getByRole('button', { name: /delete/i })
      await user.click(deleteButton)

      // Confirm deletion
      const confirmButton = await screen.findByRole('button', { name: /confirm/i })
      await user.click(confirmButton)

      // Verify part is removed
      await waitFor(() => {
        expect(screen.queryByText('Test Resistor')).not.toBeInTheDocument()
      })
    })

    it('should handle API errors gracefully', async () => {
      const { partService } = await import('../../services/parts.service')

      // Mock error response
      vi.mocked(partService.getAllParts).mockRejectedValueOnce(new Error('Failed to fetch parts'))

      render(<PartsPage />, { wrapper: createWrapper() })

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/failed to fetch parts/i)).toBeInTheDocument()
      })
    })

    it('should validate form inputs', async () => {
      const { partService } = await import('../../services/parts.service')

      vi.mocked(partService.getAllParts).mockResolvedValueOnce({
        parts: [],
        total: 0,
        page: 1,
        pageSize: 10,
      })

      render(<PartsPage />, { wrapper: createWrapper() })

      // Click add button
      const addButton = await screen.findByRole('button', { name: /add part/i })
      await user.click(addButton)

      // Try to submit empty form
      const submitButton = await screen.findByRole('button', { name: /save|add/i })
      await user.click(submitButton)

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/part name is required/i)).toBeInTheDocument()
      })

      // Enter invalid quantity
      await user.type(screen.getByLabelText(/quantity/i), '-10')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/quantity must be positive/i)).toBeInTheDocument()
      })
    })
  })

  describe('Locations CRUD Flow', () => {
    it('should handle location hierarchy correctly', async () => {
      const { locationService } = await import('../../services/location.service')

      const parentLocation = {
        id: 'parent-id',
        name: 'Storage Room A',
        description: 'Main storage room',
        children: [],
      }

      const childLocation = {
        id: 'child-id',
        name: 'Shelf 1',
        description: 'First shelf',
        parent_id: 'parent-id',
        parent: parentLocation,
      }

      vi.mocked(locationService.getAllLocations).mockResolvedValueOnce([parentLocation])

      render(<LocationsPage />, { wrapper: createWrapper() })

      // Wait for locations to load
      await waitFor(() => {
        expect(screen.getByText('Storage Room A')).toBeInTheDocument()
      })

      // Add child location
      vi.mocked(locationService.addLocation).mockResolvedValueOnce(childLocation)
      vi.mocked(locationService.getAllLocations).mockResolvedValueOnce([
        { ...parentLocation, children: [childLocation] },
      ])

      const addButton = screen.getByRole('button', { name: /add location/i })
      await user.click(addButton)

      // Fill form with parent selection
      await user.type(screen.getByLabelText(/name/i), 'Shelf 1')
      await user.type(screen.getByLabelText(/description/i), 'First shelf')

      // Select parent location
      const parentSelect = screen.getByLabelText(/parent location/i)
      await user.selectOptions(parentSelect, 'parent-id')

      const submitButton = screen.getByRole('button', { name: /save|add/i })
      await user.click(submitButton)

      // Verify hierarchy is displayed
      await waitFor(() => {
        expect(screen.getByText('Shelf 1')).toBeInTheDocument()
        // Should show as child of parent
        expect(screen.getByText(/storage room a.*shelf 1/i)).toBeInTheDocument()
      })
    })
  })

  describe('Categories CRUD Flow', () => {
    it('should prevent duplicate category names', async () => {
      const { categoryService } = await import('../../services/category.service')

      const existingCategory = {
        id: 'cat-1',
        name: 'Resistors',
        description: 'All resistor types',
      }

      vi.mocked(categoryService.getAllCategories).mockResolvedValueOnce([existingCategory])
      vi.mocked(categoryService.addCategory).mockRejectedValueOnce(
        new Error('Category with name "Resistors" already exists')
      )

      render(<CategoriesPage />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(screen.getByText('Resistors')).toBeInTheDocument()
      })

      // Try to add duplicate
      const addButton = screen.getByRole('button', { name: /add category/i })
      await user.click(addButton)

      await user.type(screen.getByLabelText(/name/i), 'Resistors')
      await user.type(screen.getByLabelText(/description/i), 'Duplicate category')

      const submitButton = screen.getByRole('button', { name: /save|add/i })
      await user.click(submitButton)

      // Should show error
      await waitFor(() => {
        expect(screen.getByText(/already exists/i)).toBeInTheDocument()
      })
    })
  })

  describe('Cross-Entity Integration', () => {
    it('should update part location and categories', async () => {
      const { partService } = await import('../../services/parts.service')
      const { locationService } = await import('../../services/location.service')
      const { categoryService } = await import('../../services/category.service')

      // Mock data
      const locations = [
        { id: 'loc-1', name: 'Drawer A1' },
        { id: 'loc-2', name: 'Drawer B2' },
      ]

      const categories = [
        { id: 'cat-1', name: 'Resistors' },
        { id: 'cat-2', name: 'Capacitors' },
      ]

      const part = {
        id: 'part-1',
        part_name: 'Test Part',
        location: locations[0],
        categories: [categories[0]],
      }

      vi.mocked(locationService.getAllLocations).mockResolvedValue(locations)
      vi.mocked(categoryService.getAllCategories).mockResolvedValue(categories)
      vi.mocked(partService.getPartById).mockResolvedValue(part)

      // Render part edit form
      render(<PartsPage />, { wrapper: createWrapper() })

      // Update location and category
      vi.mocked(partService.updatePart).mockResolvedValueOnce({
        ...part,
        location: locations[1],
        categories: [categories[1]],
      })

      // ... simulate UI interactions to change location and category

      // Verify cross-entity update
      await waitFor(() => {
        expect(partService.updatePart).toHaveBeenCalledWith(
          'part-1',
          expect.objectContaining({
            location_id: 'loc-2',
            category_names: ['Capacitors'],
          })
        )
      })
    })
  })
})
