import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import TasksManagement from '../TasksManagement'
import { tasksService } from '@/services/tasks.service'

// Mock the services
vi.mock('@/services/tasks.service')
vi.mock('@/services/parts.service')

const mockTasksService = tasksService as any



// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

// Simplified mock data for focused testing
const mockTasks = [
  {
    id: '1',
    task_type: 'part_enrichment',
    name: 'Part Enrichment',
    status: 'running',
    priority: 'normal',
    progress_percentage: 50,
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    task_type: 'csv_enrichment',
    name: 'CSV Import',
    status: 'completed',
    priority: 'high',
    progress_percentage: 100,
    created_at: new Date().toISOString(),
  },
]

const mockWorkerStatus = {
  is_running: true,
  running_tasks_count: 1,
  running_task_ids: ['1'],
  registered_handlers: 5,
}

const mockTaskStats = {
  total_tasks: 10,
  by_status: { running: 1, completed: 9 },
  by_type: { part_enrichment: 5, csv_enrichment: 5 },
  running_tasks: 1,
  failed_tasks: 0,
  completed_today: 5,
}

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TasksManagement - Focused Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock responses
    mockTasksService.getTasks.mockResolvedValue({ data: mockTasks })
    mockTasksService.getWorkerStatus.mockResolvedValue({ data: mockWorkerStatus })
    mockTasksService.getTaskStats.mockResolvedValue({ data: mockTaskStats })
  })

  describe('Basic Functionality', () => {
    it('renders the main component without crashing', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Background Tasks')).toBeInTheDocument()
      })
    })

    it('displays worker status correctly', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Worker Running')).toBeInTheDocument()
      })
    })

    it('shows task statistics', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Total Tasks')).toBeInTheDocument()
        expect(screen.getByText('Running')).toBeInTheDocument()
        expect(screen.getByText('Completed Today')).toBeInTheDocument()

        // Check for specific numbers in context
        const totalCard = screen.getByText('Total Tasks').closest('.card')
        expect(totalCard).toHaveTextContent('10')

        const runningCards = screen.getAllByText('Running')
        const runningCard = runningCards.find((card) => card.closest('.card'))?.closest('.card')
        expect(runningCard).toHaveTextContent('1')

        const completedCard = screen.getByText('Completed Today').closest('.card')
        expect(completedCard).toHaveTextContent('5')
      })
    })

    it('renders task list', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        expect(screen.getByText('CSV Import')).toBeInTheDocument()
      })
    })
  })

  describe('Worker Controls', () => {
    it('shows start worker button when worker is stopped', async () => {
      mockTasksService.getWorkerStatus.mockResolvedValue({
        data: { ...mockWorkerStatus, is_running: false },
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Start Worker')).toBeInTheDocument()
      })
    })

    it('shows stop worker button when worker is running', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Stop Worker')).toBeInTheDocument()
      })
    })
  })

  describe('Task Status Display', () => {
    it('shows correct status for running tasks', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const runningTask = screen.getByText('Part Enrichment').closest('.p-4')
        expect(runningTask?.textContent).toContain('50%')
      })
    })

    it('shows correct status for completed tasks', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const completedTask = screen.getByText('CSV Import').closest('.p-4')
        expect(completedTask?.textContent).toContain('100%')
      })
    })
  })

  describe('Quick Actions', () => {
    it('displays quick action buttons', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Update Prices')).toBeInTheDocument()
        expect(screen.getByText('Enrich All Parts')).toBeInTheDocument()
      })
    })

    it('creates price update task when button clicked', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.createQuickTask.mockResolvedValue({
        status: 'success',
        data: { id: 'new-task' },
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const updateButton = await screen.findByText('Update Prices')
      await user.click(updateButton)

      expect(mockTasksService.createQuickTask).toHaveBeenCalledWith('price-update', {
        update_all: true,
      })
    })
  })

  describe('Filtering', () => {
    it('renders filter controls', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByDisplayValue('All Status')).toBeInTheDocument()
        expect(screen.getByDisplayValue('All Types')).toBeInTheDocument()
        expect(screen.getByDisplayValue('All Priorities')).toBeInTheDocument()
      })
    })

    it('applies status filter', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const statusFilter = await screen.findByDisplayValue('All Status')
      await user.selectOptions(statusFilter, 'running')

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        expect(screen.queryByText('CSV Import')).not.toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('handles API errors gracefully', async () => {
      mockTasksService.getTasks.mockRejectedValue(new Error('Network error'))

      render(<TasksManagement />, { wrapper: TestWrapper })

      // Should still render the component structure
      await waitFor(() => {
        expect(screen.getByText('Background Tasks')).toBeInTheDocument()
      })
    })
  })
})
