import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import LoadingScreen from '../LoadingScreen'

describe('LoadingScreen', () => {
  it('renders the loading screen component', () => {
    render(<LoadingScreen />)

    // Check that the component renders
    const loadingText = screen.getByText('Loading MakerMatrix...')
    expect(loadingText).toBeInTheDocument()
  })

  it('displays the loading message', () => {
    render(<LoadingScreen />)

    // Verify the loading message is visible
    expect(screen.getByText(/Loading MakerMatrix/i)).toBeInTheDocument()
  })

  it('renders the loading spinner animations', () => {
    const { container } = render(<LoadingScreen />)

    // Check that spinner elements exist
    const spinners = container.querySelectorAll('.border-4')
    expect(spinners.length).toBeGreaterThanOrEqual(2)
  })

  it('applies correct fixed positioning classes', () => {
    const { container } = render(<LoadingScreen />)

    // Verify the container has fixed positioning
    const mainContainer = container.firstChild as HTMLElement
    expect(mainContainer).toHaveClass('fixed', 'inset-0')
  })

  it('centers content properly', () => {
    const { container } = render(<LoadingScreen />)

    // Verify flexbox centering classes
    const mainContainer = container.firstChild as HTMLElement
    expect(mainContainer).toHaveClass('flex', 'items-center', 'justify-center')
  })
})
