import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TasksManagement from '../TasksManagement'
import { tasksService } from '@/services/tasks.service'

// Set default timeout for all tests in this file
vi.setConfig({ testTimeout: 15000 })

// Mock the services
vi.mock('@/services/tasks.service')
const mockTasksService = tasksService as unknown as {
  getTasks: ReturnType<typeof vi.fn>
  getWorkerStatus: ReturnType<typeof vi.fn>
  getTaskStats: ReturnType<typeof vi.fn>
}

// Mock WebSocket service
vi.mock('@/services/task-websocket.service', () => ({
  taskWebSocket: {
    isConnected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendMessage: vi.fn(),
    startHeartbeat: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    onTaskUpdate: vi.fn(() => vi.fn()),
    onTaskCreated: vi.fn(() => vi.fn()),
    onTaskDeleted: vi.fn(() => vi.fn()),
    onWorkerStatusUpdate: vi.fn(() => vi.fn()),
    onTaskStatsUpdate: vi.fn(() => vi.fn()),
  },
}))

// Mock parts service
vi.mock('@/services/parts.service', () => ({
  partsService: {
    getAllParts: vi.fn(),
    getPartById: vi.fn(),
  },
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TasksManagement - Real-time Monitoring', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })

    // Default mock responses
    mockTasksService.getTasks.mockResolvedValue({
      data: [
        {
          id: '1',
          task_type: 'part_enrichment',
          name: 'Part Enrichment',
          status: 'running',
          priority: 'normal',
          progress_percentage: 25,
          current_step: 'Fetching data',
          created_at: new Date().toISOString(),
        },
      ],
    })

    mockTasksService.getWorkerStatus.mockResolvedValue({
      data: {
        is_running: true,
        running_tasks_count: 1,
        running_task_ids: ['1'],
        registered_handlers: 5,
      },
    })

    mockTasksService.getTaskStats.mockResolvedValue({
      data: {
        total_tasks: 10,
        by_status: { running: 1, pending: 2, completed: 7 },
        by_type: { part_enrichment: 10 },
        running_tasks: 1,
        failed_tasks: 0,
        completed_today: 5,
      },
    })
    ;(global as unknown as { fetch: typeof fetch }).fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()

      if (url.includes('/api/suppliers/configured')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: [{ id: 'digikey' }] }),
        })
      }

      if (url.includes('/api/tasks/capabilities/suppliers')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: { digikey: { capabilities: ['fetch_pricing'] } } }),
        })
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      })
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('Auto-refresh Functionality', () => {
    it('auto-refreshes data every 2 seconds by default', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial load - wait for component to mount and make initial calls
      await waitFor(
        () => {
          expect(mockTasksService.getTasks).toHaveBeenCalledTimes(1)
          expect(mockTasksService.getWorkerStatus).toHaveBeenCalledTimes(1)
          expect(mockTasksService.getTaskStats).toHaveBeenCalledTimes(1)
        },
        { timeout: 10000 }
      )

      // Fast forward 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should trigger refresh
      await waitFor(
        () => {
          expect(mockTasksService.getTasks).toHaveBeenCalledTimes(2)
          expect(mockTasksService.getWorkerStatus).toHaveBeenCalledTimes(2)
          expect(mockTasksService.getTaskStats).toHaveBeenCalledTimes(2)
        },
        { timeout: 10000 }
      )
    }, 15000)

    it('can be disabled via toggle button', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Wait for initial load
      await waitFor(
        () => {
          expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        },
        { timeout: 10000 }
      )

      // Find and click auto-refresh toggle
      const refreshButton = await screen.findByTitle('Disable fallback refresh')
      await user.click(refreshButton)

      // Reset call counts after button click
      mockTasksService.getTasks.mockClear()

      // Fast forward time
      act(() => {
        vi.advanceTimersByTime(6000) // 6 seconds
      })

      // Should not have made additional calls
      expect(mockTasksService.getTasks).not.toHaveBeenCalled()
    }, 15000)

    it('shows correct auto-refresh status', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Should show "Disable auto-refresh" initially
      await waitFor(() => {
        expect(screen.getByTitle('Disable auto-refresh')).toBeInTheDocument()
      })

      // Click to disable
      const refreshButton = screen.getByTitle('Disable auto-refresh')
      await user.click(refreshButton)

      // Should now show "Enable auto-refresh"
      await waitFor(() => {
        expect(screen.getByTitle('Enable auto-refresh')).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Progress Updates', () => {
    it('updates task progress in real-time', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial state - 25% progress
      await waitFor(() => {
        expect(screen.getByText('25%')).toBeInTheDocument()
      })

      // Mock progress update
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment',
            status: 'running',
            priority: 'normal',
            progress_percentage: 75,
            current_step: 'Processing specifications',
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show updated progress
      await waitFor(() => {
        expect(screen.getByText('75%')).toBeInTheDocument()
        expect(screen.getByText('Processing specifications')).toBeInTheDocument()
      })
    })

    it('updates current step display', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial step
      await waitFor(() => {
        expect(screen.getByText('Fetching data')).toBeInTheDocument()
      })

      // Mock step update
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment',
            status: 'running',
            priority: 'normal',
            progress_percentage: 50,
            current_step: 'Validating results',
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show new step
      await waitFor(() => {
        expect(screen.getByText('Validating results')).toBeInTheDocument()
      })
    })
  })

  describe('Task Status Changes', () => {
    it('detects when task completes', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial running state
      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
        const taskElement = screen.getByText('Part Enrichment').closest('.p-4')
        expect(taskElement?.textContent).toContain('25%')
      })

      // Mock task completion
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment',
            status: 'completed',
            priority: 'normal',
            progress_percentage: 100,
            completed_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show completed status
      await waitFor(() => {
        expect(screen.getByText('100%')).toBeInTheDocument()
        const taskElement = screen.getByText('Part Enrichment').closest('.p-4')
        expect(taskElement?.querySelector('.text-green-500')).toBeInTheDocument()
      })
    })

    it('detects when task fails', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial running state
      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
      })

      // Mock task failure
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment',
            status: 'failed',
            priority: 'normal',
            progress_percentage: 50,
            error_message: 'Connection timeout',
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show failed status
      await waitFor(() => {
        const taskElement = screen.getByText('Part Enrichment').closest('.p-4')
        expect(taskElement?.querySelector('.text-red-500')).toBeInTheDocument()
      })
    })
  })

  describe('Worker Status Monitoring', () => {
    it('detects when worker stops', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial running state
      await waitFor(() => {
        expect(screen.getByText('Worker Running')).toBeInTheDocument()
      })

      // Mock worker stop
      mockTasksService.getWorkerStatus.mockResolvedValue({
        data: {
          is_running: false,
          running_tasks_count: 0,
          running_task_ids: [],
          registered_handlers: 5,
        },
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show stopped status
      await waitFor(() => {
        expect(screen.getByText('Worker Stopped')).toBeInTheDocument()
      })
    })

    it('updates running task count', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial state
      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument() // Running count
      })

      // Mock increase in running tasks
      mockTasksService.getWorkerStatus.mockResolvedValue({
        data: {
          is_running: true,
          running_tasks_count: 3,
          running_task_ids: ['1', '2', '3'],
          registered_handlers: 5,
        },
      })

      mockTasksService.getTaskStats.mockResolvedValue({
        data: {
          total_tasks: 15,
          by_status: { running: 3, pending: 5, completed: 7 },
          by_type: { part_enrichment: 15 },
          running_tasks: 3,
          failed_tasks: 0,
          completed_today: 5,
        },
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should show updated count
      await waitFor(() => {
        expect(screen.getByText('3')).toBeInTheDocument()
      })
    })
  })

  describe('Console Real-time Updates', () => {
    it('updates console with current task step', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Open console
      const consoleButton = await screen.findByText('Console')
      await user.click(consoleButton)

      // Should show current step
      await waitFor(() => {
        expect(screen.getByText('Fetching data')).toBeInTheDocument()
      })

      // Mock step update
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment',
            status: 'running',
            priority: 'normal',
            progress_percentage: 60,
            current_step: 'Finalizing enrichment',
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Console should update
      await waitFor(() => {
        expect(screen.getByText('Finalizing enrichment')).toBeInTheDocument()
      })
    })
  })

  describe('Manual Refresh', () => {
    it('allows manual refresh', async () => {
      const user = userEvent.setup({ delay: null })
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(mockTasksService.getTasks).toHaveBeenCalledTimes(1)
      })

      // Find and click manual refresh button
      const refreshButton = screen.getByTitle('Refresh now')
      await user.click(refreshButton)

      // Should trigger additional API calls
      await waitFor(() => {
        expect(mockTasksService.getTasks).toHaveBeenCalledTimes(2)
        expect(mockTasksService.getWorkerStatus).toHaveBeenCalledTimes(2)
        expect(mockTasksService.getTaskStats).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Error Recovery', () => {
    it('continues monitoring after temporary API errors', async () => {
      render(<TasksManagement />, { wrapper: TestWrapper })

      // Initial successful load
      await waitFor(() => {
        expect(screen.getByText('Part Enrichment')).toBeInTheDocument()
      })

      // Mock API error
      mockTasksService.getTasks.mockRejectedValueOnce(new Error('Network error'))

      // Trigger refresh
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      // Should still show cached data
      expect(screen.getByText('Part Enrichment')).toBeInTheDocument()

      // Restore API success
      mockTasksService.getTasks.mockResolvedValue({
        data: [
          {
            id: '1',
            task_type: 'part_enrichment',
            name: 'Part Enrichment Updated',
            status: 'running',
            priority: 'normal',
            progress_percentage: 80,
            created_at: new Date().toISOString(),
          },
        ],
      })

      // Next refresh should work
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      await waitFor(() => {
        expect(screen.getByText('Part Enrichment Updated')).toBeInTheDocument()
      })
    })
  })
})
