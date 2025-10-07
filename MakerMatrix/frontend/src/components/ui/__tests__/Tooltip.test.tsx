import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import { Tooltip, TooltipText, TooltipIcon } from '../Tooltip'

describe('Tooltip', () => {
  describe('Basic Tooltip', () => {
    it('renders tooltip trigger', () => {
      render(
        <Tooltip content="Tooltip content">
          <button>Hover me</button>
        </Tooltip>
      )

      expect(screen.getByText('Hover me')).toBeInTheDocument()
    })

    it('shows tooltip on hover when trigger is hover', async () => {
      const user = userEvent.setup()
      render(
        <Tooltip content="Tooltip content" trigger="hover">
          Hover
        </Tooltip>
      )

      const trigger = screen.getByText('Hover')

      // Tooltip should not be visible initially
      expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument()

      // Hover over trigger
      await user.hover(trigger)

      // Tooltip should now be visible
      expect(screen.getByText('Tooltip content')).toBeInTheDocument()

      // Move mouse away
      await user.unhover(trigger)

      // Tooltip should be hidden again
      expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument()
    })

    it('shows tooltip on click when trigger is click', async () => {
      const user = userEvent.setup()
      render(
        <Tooltip content="Click content" trigger="click">
          Click me
        </Tooltip>
      )

      const trigger = screen.getByText('Click me')

      // Tooltip should not be visible initially
      expect(screen.queryByText('Click content')).not.toBeInTheDocument()

      // Click trigger
      await user.click(trigger)

      // Tooltip should be visible
      expect(screen.getByText('Click content')).toBeInTheDocument()

      // Click again to toggle
      await user.click(trigger)

      // Tooltip should be hidden
      expect(screen.queryByText('Click content')).not.toBeInTheDocument()
    })

    it('renders default icon when no children provided', () => {
      const { container } = render(<Tooltip content="Info tooltip" variant="info" />)

      // Should render the Info icon
      const icon = container.querySelector('.lucide-info')
      expect(icon).toBeInTheDocument()
    })

    it('renders help icon when variant is help', () => {
      const { container } = render(<Tooltip content="Help tooltip" variant="help" />)

      // Should render the HelpCircle icon
      const icon = container.querySelector('.lucide-help-circle')
      expect(icon).toBeInTheDocument()
    })

    it('renders warning icon when variant is warning', () => {
      const { container } = render(<Tooltip content="Warning tooltip" variant="warning" />)

      // Should render the AlertCircle icon
      const icon = container.querySelector('.lucide-alert-circle')
      expect(icon).toBeInTheDocument()
    })

    it('applies custom className', () => {
      const { container } = render(
        <Tooltip content="Test" className="custom-class">
          Test
        </Tooltip>
      )

      const wrapper = container.querySelector('.custom-class')
      expect(wrapper).toBeInTheDocument()
    })

    it('closes tooltip when clicking outside with click trigger', async () => {
      const user = userEvent.setup()
      render(
        <div>
          <Tooltip content="Click content" trigger="click">
            Click me
          </Tooltip>
          <button>Outside</button>
        </div>
      )

      // Click to open tooltip
      await user.click(screen.getByText('Click me'))
      expect(screen.getByText('Click content')).toBeInTheDocument()

      // Click outside
      await user.click(screen.getByText('Outside'))

      // Tooltip should be closed
      expect(screen.queryByText('Click content')).not.toBeInTheDocument()
    })
  })

  describe('TooltipText', () => {
    it('renders underlined text with tooltip', async () => {
      const user = userEvent.setup()
      render(<TooltipText text="Hover me" tooltip="Tooltip content" />)

      const text = screen.getByText('Hover me')
      expect(text).toBeInTheDocument()
      expect(text).toHaveClass('border-b', 'border-dotted')

      // Hover to show tooltip
      await user.hover(text)
      expect(screen.getByText('Tooltip content')).toBeInTheDocument()
    })

    it('supports different positions', async () => {
      const user = userEvent.setup()
      render(<TooltipText text="Test" tooltip="Content" position="bottom" />)

      await user.hover(screen.getByText('Test'))
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('supports different variants', async () => {
      const user = userEvent.setup()
      render(<TooltipText text="Warning" tooltip="Warning message" variant="warning" />)

      await user.hover(screen.getByText('Warning'))
      expect(screen.getByText('Warning message')).toBeInTheDocument()
    })
  })

  describe('TooltipIcon', () => {
    it('renders icon-only tooltip', () => {
      const { container } = render(<TooltipIcon tooltip="Icon tooltip" variant="info" />)

      // Should render the Info icon
      const icon = container.querySelector('.lucide-info')
      expect(icon).toBeInTheDocument()
    })

    it('shows tooltip on hover', async () => {
      const user = userEvent.setup()
      const { container } = render(<TooltipIcon tooltip="Icon content" />)

      const icon = container.querySelector('.lucide-help-circle')
      expect(icon).toBeInTheDocument()

      // Hover over icon
      if (icon?.parentElement) {
        await user.hover(icon.parentElement)
        expect(screen.getByText('Icon content')).toBeInTheDocument()
      }
    })

    it('supports custom className', () => {
      const { container } = render(<TooltipIcon tooltip="Test" className="custom-icon-class" />)

      const wrapper = container.querySelector('.custom-icon-class')
      expect(wrapper).toBeInTheDocument()
    })
  })
})
