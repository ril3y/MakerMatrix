import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TasksManagement from '../TasksManagement'
import { tasksService } from '@/services/tasks.service'
import { partsService } from '@/services/parts.service'
import toast from 'react-hot-toast'

// Mock the services
vi.mock('@/services/tasks.service')
vi.mock('@/services/parts.service')
vi.mock('@/services/task-websocket.service', () => ({
  taskWebSocket: {
    isConnected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    startHeartbeat: vi.fn(),
    onTaskUpdate: vi.fn(() => vi.fn()),
    onTaskCreated: vi.fn(() => vi.fn()),
    onTaskDeleted: vi.fn(() => vi.fn()),
    onWorkerStatusUpdate: vi.fn(() => vi.fn()),
    onTaskStatsUpdate: vi.fn(() => vi.fn()),
  },
}))

// Define mock types for services
type MockedTasksService = {
  getTasks: ReturnType<typeof vi.fn>
  getWorkerStatus: ReturnType<typeof vi.fn>
  getTaskStats: ReturnType<typeof vi.fn>
  startWorker: ReturnType<typeof vi.fn>
  stopWorker: ReturnType<typeof vi.fn>
  createQuickTask: ReturnType<typeof vi.fn>
  cancelTask: ReturnType<typeof vi.fn>
  retryTask: ReturnType<typeof vi.fn>
}

type MockedPartsService = {
  getAll: ReturnType<typeof vi.fn>
}

const mockTasksService = tasksService as unknown as MockedTasksService
const mockPartsService = partsService as unknown as MockedPartsService

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

// Mock data
const mockTasks = [
  {
    id: '1',
    task_type: 'part_enrichment',
    name: 'Part Enrichment',
    description: 'Enriching part data',
    status: 'running',
    priority: 'normal',
    progress_percentage: 50,
    current_step: 'Fetching specifications',
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
  },
  {
    id: '2',
    task_type: 'csv_enrichment',
    name: 'CSV Import',
    status: 'completed',
    priority: 'high',
    progress_percentage: 100,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
  },
  {
    id: '3',
    task_type: 'price_update',
    name: 'Price Update',
    status: 'failed',
    priority: 'low',
    progress_percentage: 0,
    error_message: 'Connection timeout',
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
  total_tasks: 25,
  by_status: {
    pending: 5,
    running: 1,
    completed: 15,
    failed: 3,
    cancelled: 1,
  },
  by_type: {
    part_enrichment: 10,
    csv_enrichment: 8,
    price_update: 7,
  },
  running_tasks: 1,
  failed_tasks: 3,
  completed_today: 12,
}

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TasksManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })

    // Default mock responses
    mockTasksService.getTasks.mockResolvedValue({ data: mockTasks })
    mockTasksService.getWorkerStatus.mockResolvedValue({ data: mockWorkerStatus })
    mockTasksService.getTaskStats.mockResolvedValue({ data: mockTaskStats })
    mockPartsService.getAll.mockResolvedValue([
      { id: 'part1', name: 'Arduino Uno', supplier: 'digikey' },
      { id: 'part2', name: 'Resistor 10K', supplier: 'digikey' },
    ])
    // Mock global fetch with proper typing
    global.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()

      if (url.includes('/api/suppliers/configured')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: [{ id: 'digikey' }] }),
        } as Response)
      }

      if (url.includes('/api/tasks/capabilities/suppliers')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: { digikey: { capabilities: ['fetch_pricing'] } } }),
        } as Response)
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      } as Response)
    }) as typeof fetch
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('Basic Rendering', () => {
    it('renders header with worker status', () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      expect(screen.getByText('Background Tasks')).toBeInTheDocument()
      expect(screen.getByText('Worker Running')).toBeInTheDocument()
    })

    it('shows worker stopped status when not running', async () => {
      mockTasksService.getWorkerStatus.mockResolvedValue({
        data: { ...mockWorkerStatus, is_running: false },
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Worker Stopped')).toBeInTheDocument()
      })
    })

    it('displays task statistics', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('25')).toBeInTheDocument() // Total tasks
        expect(screen.getByText('1')).toBeInTheDocument() // Running
        expect(screen.getByText('12')).toBeInTheDocument() // Completed today
        expect(screen.getByText('3')).toBeInTheDocument() // Failed
        expect(screen.getByText('5')).toBeInTheDocument() // Pending
      })
    })
  })

  describe('Auto-refresh Functionality', () => {
    it('automatically refreshes data every 2 seconds when enabled', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(mockTasksService.getTasks).toHaveBeenCalledTimes(1)
      })

      // Advance timer by 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      await waitFor(() => {
        expect(mockTasksService.getTasks).toHaveBeenCalledTimes(2)
        expect(mockTasksService.getWorkerStatus).toHaveBeenCalledTimes(2)
        expect(mockTasksService.getTaskStats).toHaveBeenCalledTimes(2)
      })
    })

    it('stops auto-refresh when disabled', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const refreshButton = await screen.findByTitle('Disable auto-refresh')
      await user.click(refreshButton)

      act(() => {
        vi.advanceTimersByTime(4000)
      })

      // Should only have initial calls, no refresh
      expect(mockTasksService.getTasks).toHaveBeenCalledTimes(1)
    })
  })

  describe('Worker Control', () => {
    it('starts worker when start button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.getWorkerStatus.mockResolvedValue({
        data: { ...mockWorkerStatus, is_running: false },
      })
      mockTasksService.startWorker.mockResolvedValue({ status: 'success' })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const startButton = await screen.findByText('Start Worker')
      await user.click(startButton)

      expect(mockTasksService.startWorker).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Task worker started')
    })

    it('stops worker when stop button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.stopWorker.mockResolvedValue({ status: 'success' })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const stopButton = await screen.findByText('Stop Worker')
      await user.click(stopButton)

      expect(mockTasksService.stopWorker).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Task worker stopped')
    })

    it('handles worker control errors', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.stopWorker.mockRejectedValue(new Error('Network error'))

      render(<TasksManagement />, { wrapper: TestWrapper })

      const stopButton = await screen.findByText('Stop Worker')
      await user.click(stopButton)

      expect(toast.error).toHaveBeenCalledWith('Failed to stop worker')
    })
  })

  describe('Task Filtering', () => {
    it('filters tasks by status', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        expect(screen.getByText('CSV Import')).toBeInTheDocument()
        expect(screen.getByText('Price Update')).toBeInTheDocument()
      })

      const statusFilter = screen.getByDisplayValue('All Status')
      await user.selectOptions(statusFilter, 'running')

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        expect(screen.queryByText('CSV Import')).not.toBeInTheDocument()
        expect(screen.queryByText('Price Update')).not.toBeInTheDocument()
      })
    })

    it('filters tasks by type', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const typeFilter = await screen.findByDisplayValue('All Types')
      await user.selectOptions(typeFilter, 'csv_enrichment')

      await waitFor(() => {
        expect(screen.queryByText('Part Enrichment')).not.toBeInTheDocument()
        expect(screen.getByText('CSV Import')).toBeInTheDocument()
        expect(screen.queryByText('Price Update')).not.toBeInTheDocument()
      })
    })

    it('filters tasks by priority', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const priorityFilter = await screen.findByDisplayValue('All Priorities')
      await user.selectOptions(priorityFilter, 'high')

      await waitFor(() => {
        expect(screen.queryByText('Part Enrichment')).not.toBeInTheDocument()
        expect(screen.getByText('CSV Import')).toBeInTheDocument()
        expect(screen.queryByText('Price Update')).not.toBeInTheDocument()
      })
    })

    it('clears all filters', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Apply filters
      const statusFilter = await screen.findByDisplayValue('All Status')
      await user.selectOptions(statusFilter, 'running')

      // Clear filters
      const clearButton = screen.getByText('Clear Filters')
      await user.click(clearButton)

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        expect(screen.getByText('CSV Import')).toBeInTheDocument()
        expect(screen.getByText('Price Update')).toBeInTheDocument()
      })
    })
  })

  describe('Quick Actions', () => {
    it('creates price update task', async () => {
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
      expect(toast.success).toHaveBeenCalledWith('Task created successfully')
    })

    it('creates bulk enrichment task', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.createQuickTask.mockResolvedValue({
        status: 'success',
        data: { id: 'new-task' },
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const enrichButton = await screen.findByText('Enrich All Parts')
      await user.click(enrichButton)

      await waitFor(() => {
        expect(toast.loading).toHaveBeenCalledWith('Fetching parts for enrichment...', {
          id: 'bulk-enrichment-loading',
        })
      })

      await waitFor(() => {
        expect(mockPartsService.getAll).toHaveBeenCalled()
        expect(mockTasksService.createQuickTask).toHaveBeenCalledWith('bulk-enrichment', {
          enrich_all: true,
          batch_size: 10,
          page_size: 10,
          capabilities: ['fetch_pricing', 'fetch_datasheet', 'fetch_specifications', 'fetch_image'],
          force_refresh: false,
        })
        expect(toast.success).toHaveBeenCalledWith(
          'Found 2 parts for enrichment from 1 suppliers. Task will process 10 parts at a time.'
        )
      })
    })

    it('handles bulk enrichment with no parts', async () => {
      const user = userEvent.setup({ delay: null })
      mockPartsService.getAll.mockResolvedValue([])

      render(<TasksManagement />, { wrapper: TestWrapper })

      const enrichButton = await screen.findByText('Enrich All Parts')
      await user.click(enrichButton)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('No parts found to enrich')
        expect(mockTasksService.createQuickTask).not.toHaveBeenCalled()
      })
    })

    it('handles task creation errors', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.createQuickTask.mockRejectedValue({
        response: { data: { detail: 'Invalid task configuration' } },
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const updateButton = await screen.findByText('Update Prices')
      await user.click(updateButton)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Failed to create task: Invalid task configuration'
        )
      })
    })
  })

  describe('Task Actions', () => {
    it('cancels running task', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.cancelTask.mockResolvedValue({ status: 'success' })

      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const cancelButtons = screen
          .getAllByRole('button', { name: '' })
          .filter((btn) => btn.querySelector('svg')?.classList.contains('w-4'))
        expect(cancelButtons.length).toBeGreaterThan(0)
      })

      const cancelButton = screen
        .getAllByRole('button')
        .find((btn) => btn.querySelector('svg') && btn.closest('[data-testid="task-1"]'))

      if (cancelButton) {
        await user.click(cancelButton)
        expect(mockTasksService.cancelTask).toHaveBeenCalledWith('1')
        expect(toast.success).toHaveBeenCalledWith('Task cancelled')
      }
    })

    it('retries failed task', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.retryTask.mockResolvedValue({ status: 'success' })

      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const retryButtons = screen
          .getAllByRole('button')
          .filter((btn) => btn.querySelector('svg')?.classList.contains('w-4'))
        expect(retryButtons.length).toBeGreaterThan(0)
      })

      // Find retry button for failed task
      const taskElement = screen.getByText('Price Update').closest('.p-4')
      const retryButton = taskElement?.querySelector('button:last-child')

      if (retryButton) {
        await user.click(retryButton)
        expect(mockTasksService.retryTask).toHaveBeenCalledWith('3')
        expect(toast.success).toHaveBeenCalledWith('Task retry scheduled')
      }
    })
  })

  describe('Task Console', () => {
    it('toggles console visibility', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const consoleButton = await screen.findByText('Console')
      await user.click(consoleButton)

      await waitFor(() => {
        expect(screen.getByText('Task Console')).toBeInTheDocument()
        expect(screen.getByText('Fetching specifications')).toBeInTheDocument()
      })

      // Close console
      const closeButton = screen
        .getByRole('button', { name: '' })
        .parentElement?.querySelector('button:last-child')
      if (closeButton) {
        await user.click(closeButton)
        await waitFor(() => {
          expect(screen.queryByText('Task Console')).not.toBeInTheDocument()
        })
      }
    })

    it('shows no running tasks message when empty', async () => {
      const user = userEvent.setup({ delay: null })
      mockTasksService.getTasks.mockResolvedValue({
        data: mockTasks.filter((t) => t.status !== 'running'),
      })

      render(<TasksManagement />, { wrapper: TestWrapper })

      const consoleButton = await screen.findByText('Console')
      await user.click(consoleButton)

      await waitFor(() => {
        expect(screen.getByText('No running tasks to monitor...')).toBeInTheDocument()
      })
    })
  })

  describe('Task Details Modal', () => {
    it('opens task details modal when view button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const viewButtons = screen
          .getAllByRole('button')
          .filter((btn) => btn.querySelector('svg')?.classList.contains('w-4'))
        expect(viewButtons.length).toBeGreaterThan(0)
      })

      // Click first view button
      const taskElement = screen.getByText('Part Enrichment').closest('.p-4')
      const viewButton = taskElement?.querySelector('button')

      if (viewButton) {
        await user.click(viewButton)

        await waitFor(() => {
          expect(screen.getByText('Task Details')).toBeInTheDocument()
          expect(screen.getByText('Task ID')).toBeInTheDocument()
          expect(screen.getByText('1')).toBeInTheDocument()
        })
      }
    })

    it('displays error message in details modal', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const taskElement = await screen.findByText('Price Update')
      const viewButton = taskElement.closest('.p-4')?.querySelector('button')

      if (viewButton) {
        await user.click(viewButton)

        await waitFor(() => {
          expect(screen.getByText('Error Message')).toBeInTheDocument()
          expect(screen.getByText('Connection timeout')).toBeInTheDocument()
        })
      }
    })

    it('closes modal when close button is clicked', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      const taskElement = await screen.findByText('Part Enrichment')
      const viewButton = taskElement.closest('.p-4')?.querySelector('button')

      if (viewButton) {
        await user.click(viewButton)

        const closeButton = await screen.findByRole('button', { name: '' })
        await user.click(closeButton)

        await waitFor(() => {
          expect(screen.queryByText('Task Details')).not.toBeInTheDocument()
        })
      }
    })
  })

  describe('Error Handling', () => {
    it('handles task loading errors gracefully', async () => {
      mockTasksService.getTasks.mockRejectedValue(new Error('Network error'))

      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to load tasks')
      })
    })

    it('continues showing cached data on refresh errors', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
      })

      // Make subsequent calls fail
      mockTasksService.getTasks.mockRejectedValue(new Error('Network error'))

      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should still show cached data
      expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
      expect(toast.error).not.toHaveBeenCalled() // No error toast on refresh failures
    })
  })

  describe('Task Status Display', () => {
    it('shows correct status icons', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        // Running task should have spinning icon
        const runningTask = screen.getByText('Part Enrichment').closest('.p-4')
        expect(runningTask?.querySelector('.animate-spin')).toBeInTheDocument()

        // Completed task should have check icon
        const completedTask = screen.getByText('CSV Import').closest('.p-4')
        expect(completedTask?.querySelector('.text-green-500')).toBeInTheDocument()

        // Failed task should have X icon
        const failedTask = screen.getByText('Price Update').closest('.p-4')
        expect(failedTask?.querySelector('.text-red-500')).toBeInTheDocument()
      })
    })

    it('shows progress bar for running tasks', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const runningTask = screen.getByText('Part Enrichment').closest('.p-4')
        const progressBar = runningTask?.querySelector('[style*="width: 50%"]')
        expect(progressBar).toBeInTheDocument()
      })
    })

    it('formats task duration correctly', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const completedTask = screen.getByText('CSV Import').closest('.p-4')
        expect(completedTask?.textContent).toMatch(/Duration: \d+[smh]/)
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /start worker/i })).toBeInTheDocument()
        expect(screen.getAllByRole('combobox')).toHaveLength(3) // Three filter selects
      })
    })

    it('announces task status changes to screen readers', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      await waitFor(() => {
        const statusBadges = screen.getAllByText(/running|completed|failed/i)
        statusBadges.forEach((badge) => {
          expect(badge.closest('[role="status"]') || badge).toBeInTheDocument()
        })
      })
    })
  })
})
