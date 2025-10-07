import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TasksPage from '../TasksPage'
import { tasksService } from '@/services/tasks.service'
import { partsService } from '@/services/parts.service'

// Mock the services
vi.mock('@/services/tasks.service')
vi.mock('@/services/parts.service')

const mockTasksService = tasksService as any
const mockPartsService = partsService as any

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

// Mock TasksManagement component
vi.mock('@/components/tasks/TasksManagement', () => ({
  default: () => <div data-testid="tasks-management">Tasks Management Component</div>,
}))

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TasksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Basic Rendering', () => {
    it('renders page header and title correctly', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      expect(screen.getByText('Background Tasks')).toBeInTheDocument()
      expect(
        screen.getByText('Monitor and manage background tasks and processes')
      ).toBeInTheDocument()
    })

    it('renders TasksManagement component', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      expect(screen.getByTestId('tasks-management')).toBeInTheDocument()
    })

    it('displays activity icon in header', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const header = screen.getByText('Background Tasks')
      expect(header.querySelector('svg')).toBeInTheDocument()
    })
  })

  describe('Animation', () => {
    it('applies animation classes to header', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const headerContainer = screen.getByText('Background Tasks').closest('div')?.parentElement
      expect(headerContainer).toHaveAttribute('initial')
      expect(headerContainer).toHaveAttribute('animate')
    })

    it('applies animation classes to content', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const contentContainer = screen.getByTestId('tasks-management').parentElement
      expect(contentContainer).toHaveAttribute('initial')
      expect(contentContainer).toHaveAttribute('animate')
      expect(contentContainer).toHaveAttribute('transition')
    })
  })

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('Background Tasks')
    })

    it('provides descriptive text for screen readers', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      expect(
        screen.getByText('Monitor and manage background tasks and processes')
      ).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('uses proper spacing classes', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const container = screen.getByText('Background Tasks').closest('.space-y-6')
      expect(container).toHaveClass('space-y-6')
    })

    it('maintains consistent page structure', () => {
      render(<TasksPage />, { wrapper: TestWrapper })

      const pageContainer = screen.getByText('Background Tasks').closest('div')
        ?.parentElement?.parentElement
      expect(pageContainer).toBeInTheDocument()
      expect(pageContainer?.children).toHaveLength(2) // Header and content
    })
  })
})
