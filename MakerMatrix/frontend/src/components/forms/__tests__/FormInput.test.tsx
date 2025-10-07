import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import FormInput from '../FormInput'

describe('FormInput', () => {
  it('renders with a label', () => {
    render(<FormInput label="Username" />)

    expect(screen.getByText('Username')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('displays required indicator when required prop is true', () => {
    render(<FormInput label="Email" required />)

    const requiredIndicator = screen.getByText('*')
    expect(requiredIndicator).toBeInTheDocument()
    expect(requiredIndicator).toHaveClass('text-red-500')
  })

  it('displays error message when error prop is provided', () => {
    render(<FormInput label="Password" error="Password is required" />)

    expect(screen.getByText('Password is required')).toBeInTheDocument()
  })

  it('displays description text when description prop is provided', () => {
    render(<FormInput label="API Key" description="Enter your API key from settings" />)

    expect(screen.getByText('Enter your API key from settings')).toBeInTheDocument()
  })

  it('renders different input types correctly', () => {
    const { container, rerender } = render(<FormInput label="Text Input" type="text" />)
    let input = container.querySelector('input[type="text"]')
    expect(input).toBeInTheDocument()

    rerender(<FormInput label="Email Input" type="email" />)
    input = container.querySelector('input[type="email"]')
    expect(input).toBeInTheDocument()

    rerender(<FormInput label="Password Input" type="password" />)
    input = container.querySelector('input[type="password"]')
    expect(input).toBeInTheDocument()
  })

  it('applies error styling when error is present', () => {
    const { container } = render(<FormInput label="Field" error="Error message" />)

    const input = container.querySelector('input')
    expect(input).toHaveClass('border-red-500')
  })

  it('handles disabled state correctly', () => {
    render(<FormInput label="Disabled Field" disabled />)

    const input = screen.getByRole('textbox')
    expect(input).toBeDisabled()
    expect(input).toHaveClass('disabled:bg-theme-tertiary')
  })

  it('allows user input', async () => {
    const user = userEvent.setup()
    render(<FormInput label="Name" />)

    const input = screen.getByRole('textbox') as HTMLInputElement
    await user.type(input, 'John Doe')

    expect(input.value).toBe('John Doe')
  })

  it('forwards placeholder prop correctly', () => {
    render(<FormInput label="Search" placeholder="Enter search term..." />)

    expect(screen.getByPlaceholderText('Enter search term...')).toBeInTheDocument()
  })

  it('supports custom className on field', () => {
    const { container } = render(<FormInput label="Custom" className="custom-class" />)

    const formField = container.querySelector('.custom-class')
    expect(formField).toBeInTheDocument()
  })

  it('applies default type as text when type is not specified', () => {
    const { container } = render(<FormInput label="Default Type" />)

    const input = container.querySelector('input')
    expect(input).toHaveAttribute('type', 'text')
  })
})
