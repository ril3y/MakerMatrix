import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import TasksManagement from '../TasksManagement'
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

describe('TasksManagement - Basic Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock responses
    mockTasksService.getTasks.mockResolvedValue({ data: mockTasks })
    mockTasksService.getWorkerStatus.mockResolvedValue({ data: mockWorkerStatus })
    mockTasksService.getTaskStats.mockResolvedValue({ data: mockTaskStats })
    mockPartsService.getAll.mockResolvedValue([
      { id: 'part1', name: 'Arduino Uno' },
      { id: 'part2', name: 'Resistor 10K' },
    ])
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('renders header with worker status', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      expect(screen.getByText('Background Tasks')).toBeInTheDocument()
      expect(screen.getByText('Worker Running')).toBeInTheDocument()
    })
  })

  it('displays task statistics', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument() // Total tasks
      expect(screen.getByText('1')).toBeInTheDocument() // Running
      expect(screen.getByText('12')).toBeInTheDocument() // Completed today
    })
  })

  it('displays task list', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      // Look for the task name in the task list, not in filters
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
      expect(screen.getByText('Create Custom Task')).toBeInTheDocument()
    })
  })

  it('shows filter controls', async () => {
    render(<TasksManagement />, { wrapper: TestWrapper })

    await waitFor(() => {
      expect(screen.getByDisplayValue('All Status')).toBeInTheDocument()
      expect(screen.getByDisplayValue('All Types')).toBeInTheDocument()
      expect(screen.getByDisplayValue('All Priorities')).toBeInTheDocument()
    })
  })
})
