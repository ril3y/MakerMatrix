import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TasksManagement from '../TasksManagement'
import { tasksService } from '@/services/tasks.service'
import { partsService } from '@/services/parts.service'

// Mock the services
vi.mock('@/services/tasks.service')
vi.mock('@/services/parts.service')

// Mock the WebSocket service so useTasksDashboard does not attempt a real connection
vi.mock('@/services/task-websocket.service', () => ({
  taskWebSocket: {
    isConnected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
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

const mockTasksService = vi.mocked(tasksService)
const mockPartsService = vi.mocked(partsService)

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

const mockTasks = [
  {
    id: '1',
    task_type: 'part_enrichment',
    name: 'Part Enrichment',
    description: 'Enriching part data',
    status: 'running' as const,
    priority: 'normal' as const,
    progress_percentage: 50,
    current_step: 'Fetching specifications',
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    max_retries: 3,
    retry_count: 0,
    depends_on_task_ids: [],
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
  by_priority: {
    low: 8,
    normal: 12,
    high: 4,
    urgent: 1,
  },
  running_tasks: 1,
  failed_tasks: 3,
  completed_today: 12,
}

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('TasksManagement - Basic Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock responses
    mockTasksService.getTasks.mockResolvedValue({ status: 'success', data: mockTasks, total: 1 })
    mockTasksService.getWorkerStatus.mockResolvedValue({
      status: 'success',
      data: mockWorkerStatus,
    })
    mockTasksService.getTaskStats.mockResolvedValue({ status: 'success', data: mockTaskStats })
    mockPartsService.getAll.mockResolvedValue([
      {
        id: 'part1',
        name: 'Arduino Uno',
        quantity: 10,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 'part2',
        name: 'Resistor 10K',
        quantity: 100,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ])

    // useTasksDashboard uses raw fetch() for /api/suppliers/configured and
    // /api/tasks/capabilities/suppliers — stub it so MSW does not error.
    ;(global as unknown as { fetch: typeof fetch }).fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.includes('/api/suppliers/configured')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: [] }),
        } as Response)
      }
      if (url.includes('/api/tasks/capabilities/suppliers')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ data: {} }),
        } as Response)
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response)
    }) as unknown as typeof fetch
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('renders worker status badge', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      expect(screen.getByText('Worker Running')).toBeInTheDocument()
    })
  })

  it('displays task statistics', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      // Total tasks card
      expect(screen.getByText('Total Tasks')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
      expect(screen.getByText('Completed Today')).toBeInTheDocument()
      expect(screen.getByText('12')).toBeInTheDocument()
    })
  })

  it('displays task list', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      // Look for the task name as an H5 inside the task list
      const taskElements = screen.getAllByText('Part Enrichment')
      const taskInList = taskElements.find((el) => el.tagName === 'H5')
      expect(taskInList).toBeInTheDocument()
      expect(screen.getByText('Fetching specifications')).toBeInTheDocument()
    })
  })

  it('shows quick action buttons', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      expect(screen.getByText('Update Prices')).toBeInTheDocument()
      expect(screen.getByText('Enrich All Parts')).toBeInTheDocument()
      expect(screen.getByText('Clean Database')).toBeInTheDocument()
    })
  })

  it('shows filter controls', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    // The component renders CustomSelect dropdowns whose initial labels are
    // "All Status", "All Types", "All Priorities".
    await waitFor(() => {
      expect(screen.getByText('All Status')).toBeInTheDocument()
      expect(screen.getByText('All Types')).toBeInTheDocument()
      expect(screen.getByText('All Priorities')).toBeInTheDocument()
    })
  })
})
