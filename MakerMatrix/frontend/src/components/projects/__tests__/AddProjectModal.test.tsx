import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import userEvent from '@testing-library/user-event'
import { toast } from 'react-hot-toast'
import AddProjectModal from '../AddProjectModal'
import { projectsService } from '@/services/projects.service'
import type { Project } from '@/types/projects'

// Mock dependencies
vi.mock('react-hot-toast')
vi.mock('@/services/projects.service')
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
}))

const mockProjectsService = vi.mocked(projectsService)
const mockToast = vi.mocked(toast)

describe('AddProjectModal - Core Functionality', () => {
  const existingProjects = ['golfcart-harness', 'led-panel', 'arduino-robot']

  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
    existingProjects,
  }

  const mockCreatedProject: Project = {
    id: 'proj-123',
    name: 'test-project',
    description: 'Test project description',
    status: 'planning',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful project creation by default
    mockProjectsService.createProject.mockResolvedValue(mockCreatedProject)
  })

  describe('Basic Rendering', () => {
    it('should render modal with title and form fields', () => {
      render(<AddProjectModal {...mockProps} />)

      expect(screen.getByText('Add New Project')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., golfcart-harness')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Brief description of the project (optional)')).toBeInTheDocument()
      expect(screen.getByText('Create Project')).toBeInTheDocument()
    })

    it('should show status dropdown with all options', () => {
      render(<AddProjectModal {...mockProps} />)

      const statusSelect = screen.getByDisplayValue('Planning')
      expect(statusSelect).toBeInTheDocument()
    })

    it('should have default status as planning', () => {
      render(<AddProjectModal {...mockProps} />)

      const statusSelect = screen.getByDisplayValue('Planning')
      expect(statusSelect).toHaveValue('planning')
    })

    it('should show links section', () => {
      render(<AddProjectModal {...mockProps} />)

      expect(screen.getByText('Links')).toBeInTheDocument()
      expect(screen.getByText('Add Link')).toBeInTheDocument()
    })

    it('should show image upload field', () => {
      render(<AddProjectModal {...mockProps} />)

      expect(screen.getByText('Project Image')).toBeInTheDocument()
      expect(screen.getByText('Upload an image for the project')).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('should show error when submitting without project name', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      expect(screen.getByText('Project name is required')).toBeInTheDocument()
      expect(mockProjectsService.createProject).not.toHaveBeenCalled()
    })

    it('should show error for duplicate project name', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'golfcart-harness') // Existing project

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      expect(screen.getByText('A project with this name already exists')).toBeInTheDocument()
    })

    it('should be case insensitive for duplicate check', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'GOLFCART-HARNESS') // Different case

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      expect(screen.getByText('A project with this name already exists')).toBeInTheDocument()
    })
  })

  describe('Links Management', () => {
    it('should add a new link when Add Link button is clicked', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)

      const linkNameInputs = screen.getAllByPlaceholderText('Link name (e.g., GitHub)')
      expect(linkNameInputs).toHaveLength(1)

      const linkUrlInputs = screen.getAllByPlaceholderText('URL (e.g., https://github.com/...)')
      expect(linkUrlInputs).toHaveLength(1)
    })

    it('should allow multiple links to be added', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const addLinkButton = screen.getByText('Add Link')

      await user.click(addLinkButton)
      await user.click(addLinkButton)
      await user.click(addLinkButton)

      const linkNameInputs = screen.getAllByPlaceholderText('Link name (e.g., GitHub)')
      expect(linkNameInputs).toHaveLength(3)
    })

    it('should remove link when X button is clicked', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)
      await user.click(addLinkButton)

      let linkNameInputs = screen.getAllByPlaceholderText('Link name (e.g., GitHub)')
      expect(linkNameInputs).toHaveLength(2)

      // Click the first X button
      const removeButtons = screen.getAllByRole('button').filter((btn) =>
        btn.querySelector('svg')?.classList.contains('lucide-x')
      )
      await user.click(removeButtons[0])

      linkNameInputs = screen.queryAllByPlaceholderText('Link name (e.g., GitHub)')
      expect(linkNameInputs).toHaveLength(1)
    })

    it('should show empty state when no links added', () => {
      render(<AddProjectModal {...mockProps} />)

      expect(screen.getByText('No links added. Click "Add Link" to include project-related URLs (GitHub, documentation, etc.)')).toBeInTheDocument()
    })

    it('should allow entering link data', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)

      const linkNameInput = screen.getByPlaceholderText('Link name (e.g., GitHub)')
      const linkUrlInput = screen.getByPlaceholderText('URL (e.g., https://github.com/...)')

      await user.type(linkNameInput, 'GitHub')
      await user.type(linkUrlInput, 'https://github.com/test/repo')

      expect(linkNameInput).toHaveValue('GitHub')
      expect(linkUrlInput).toHaveValue('https://github.com/test/repo')
    })
  })

  describe('Status Selection', () => {
    it('should allow changing project status', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const statusSelect = screen.getByDisplayValue('Planning')
      await user.selectOptions(statusSelect, 'active')

      expect(statusSelect).toHaveValue('active')
    })

    it('should have all status options available', async () => {
      render(<AddProjectModal {...mockProps} />)

      const statusSelect = screen.getByDisplayValue('Planning')
      const options = Array.from(statusSelect.querySelectorAll('option'))

      const optionValues = options.map((opt) => opt.value)
      expect(optionValues).toContain('planning')
      expect(optionValues).toContain('active')
      expect(optionValues).toContain('completed')
      expect(optionValues).toContain('archived')
    })
  })

  describe('Project Creation', () => {
    it('should create project successfully with minimum required fields', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'new-project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith({
          name: 'new-project',
          description: '',
          status: 'planning',
          image_url: undefined,
          links: undefined,
        })
      })

      expect(mockToast.success).toHaveBeenCalledWith('Project created successfully')
      expect(mockProps.onSuccess).toHaveBeenCalled()
      expect(mockProps.onClose).toHaveBeenCalled()
    })

    it('should create project with description', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      const descriptionInput = screen.getByPlaceholderText('Brief description of the project (optional)')

      await user.type(nameInput, 'new-project')
      await user.type(descriptionInput, 'This is a test project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'new-project',
            description: 'This is a test project',
          })
        )
      })
    })

    it('should create project with links', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'new-project')

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)

      const linkNameInput = screen.getByPlaceholderText('Link name (e.g., GitHub)')
      const linkUrlInput = screen.getByPlaceholderText('URL (e.g., https://github.com/...)')

      await user.type(linkNameInput, 'GitHub')
      await user.type(linkUrlInput, 'https://github.com/test/repo')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'new-project',
            links: {
              GitHub: 'https://github.com/test/repo',
            },
          })
        )
      })
    })

    it('should trim whitespace from link keys and values', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'new-project')

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)

      const linkNameInput = screen.getByPlaceholderText('Link name (e.g., GitHub)')
      const linkUrlInput = screen.getByPlaceholderText('URL (e.g., https://github.com/...)')

      await user.type(linkNameInput, '  GitHub  ')
      await user.type(linkUrlInput, '  https://github.com/test/repo  ')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith(
          expect.objectContaining({
            links: {
              GitHub: 'https://github.com/test/repo',
            },
          })
        )
      })
    })

    it('should ignore empty links when creating project', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'new-project')

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)
      await user.click(addLinkButton)

      // Fill only the first link
      const linkNameInputs = screen.getAllByPlaceholderText('Link name (e.g., GitHub)')
      const linkUrlInputs = screen.getAllByPlaceholderText('URL (e.g., https://github.com/...)')

      await user.type(linkNameInputs[0], 'GitHub')
      await user.type(linkUrlInputs[0], 'https://github.com/test/repo')
      // Leave second link empty

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith(
          expect.objectContaining({
            links: {
              GitHub: 'https://github.com/test/repo',
            },
          })
        )
      })
    })

    it('should handle creation API error', async () => {
      const user: UserEvent = userEvent.setup()
      mockProjectsService.createProject.mockRejectedValueOnce({
        response: { data: { detail: 'Project already exists' } },
      })

      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'test-project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Project already exists')
      })

      expect(mockProps.onSuccess).not.toHaveBeenCalled()
    })

    it('should handle generic API error', async () => {
      const user: UserEvent = userEvent.setup()
      mockProjectsService.createProject.mockRejectedValueOnce(new Error('Network error'))

      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'test-project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to create project')
      })
    })
  })

  describe('Form Reset and Modal Close', () => {
    it('should reset form when modal is closed', async () => {
      const user: UserEvent = userEvent.setup()
      const { unmount } = render(<AddProjectModal {...mockProps} />)

      // Fill in some data
      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'Test Project')

      // Close modal
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      expect(mockProps.onClose).toHaveBeenCalled()

      // Clean up the first render
      unmount()

      // Reopen modal and check form is reset
      render(<AddProjectModal {...mockProps} />)

      const resetNameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      expect(resetNameInput).toHaveValue('')
    })

    it('should clear links when modal is closed', async () => {
      const user: UserEvent = userEvent.setup()
      const { unmount } = render(<AddProjectModal {...mockProps} />)

      const addLinkButton = screen.getByText('Add Link')
      await user.click(addLinkButton)

      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      unmount()
      render(<AddProjectModal {...mockProps} />)

      const linkInputs = screen.queryAllByPlaceholderText('Link name (e.g., GitHub)')
      expect(linkInputs).toHaveLength(0)
    })
  })

  describe('Loading States', () => {
    it('should disable buttons during creation', async () => {
      const user: UserEvent = userEvent.setup()

      // Make createProject hang to test loading state
      mockProjectsService.createProject.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'Test Project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      // Check loading state
      await waitFor(() => {
        expect(screen.getByText('Creating...')).toBeInTheDocument()
        expect(screen.getByText('Creating...')).toBeDisabled()
        expect(screen.getByText('Cancel')).toBeDisabled()
      })
    })

    it('should show loading spinner during creation', async () => {
      const user: UserEvent = userEvent.setup()

      mockProjectsService.createProject.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'Test Project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      // Check for spinner
      await waitFor(() => {
        const spinner = document.querySelector('.animate-spin')
        expect(spinner).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle modal when closed', () => {
      render(<AddProjectModal {...mockProps} isOpen={false} />)

      // Modal content should not be visible
      expect(screen.queryByText('Add New Project')).not.toBeInTheDocument()
    })

    it('should handle modal with no existing projects', () => {
      render(<AddProjectModal {...mockProps} existingProjects={[]} />)

      expect(screen.getByText('Add New Project')).toBeInTheDocument()
    })

    it('should support lowercase with hyphens naming convention', async () => {
      const user: UserEvent = userEvent.setup()
      render(<AddProjectModal {...mockProps} />)

      const nameInput = screen.getByPlaceholderText('e.g., golfcart-harness')
      await user.type(nameInput, 'my-awesome-project')

      const submitButton = screen.getByText('Create Project')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockProjectsService.createProject).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'my-awesome-project',
          })
        )
      })
    })
  })
})
