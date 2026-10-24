/**
 * Accessibility tests for the shared `Modal` component. Covers the contract
 * the audit asked us to add: dialog semantics, focus trap on Tab, and focus
 * restore on close.
 *
 * Note: the global test setup mocks `framer-motion` with a function
 * component that does NOT forward refs. The Modal stores a ref on its
 * `motion.div` to find focusable descendants, so we override the mock here
 * with a forwardRef-aware version. We also stub out the `Modal`'s portal so
 * the rendered tree lives inside the testing-library container.
 */
import type { ReactNode } from 'react'
import { createElement, forwardRef, useState } from 'react'
import { describe, it, expect, afterEach, vi } from 'vitest'

vi.mock('framer-motion', () => {
  type MotionMockProps = { children?: ReactNode } & Record<string, unknown>
  const createMotionComponent = (tag: string) =>
    forwardRef<HTMLElement, MotionMockProps>(function MotionMock(props, ref) {
      const { children, ...rest } = props
      return createElement(tag, { ...rest, ref }, children as ReactNode)
    })

  return {
    motion: {
      div: createMotionComponent('div'),
      button: createMotionComponent('button'),
      span: createMotionComponent('span'),
      p: createMotionComponent('p'),
      a: createMotionComponent('a'),
      form: createMotionComponent('form'),
      li: createMotionComponent('li'),
      ul: createMotionComponent('ul'),
    },
    AnimatePresence: ({ children }: { children: ReactNode }) => children,
    useAnimation: () => ({ start: vi.fn(), set: vi.fn() }),
    useInView: () => true,
  }
})

import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import Modal from '../Modal'

afterEach(() => {
  cleanup()
})

describe('Modal a11y', () => {
  it('exposes dialog role + aria-modal + aria-labelledby wired to the title', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Test Dialog">
        <p>Body content</p>
      </Modal>
    )

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')

    const titleId = dialog.getAttribute('aria-labelledby')
    expect(titleId).toBeTruthy()

    const heading = document.getElementById(titleId as string)
    expect(heading).not.toBeNull()
    expect(heading?.textContent).toBe('Test Dialog')
  })

  it('labels the close button for screen readers', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="X">
        <p>Body</p>
      </Modal>
    )
    const closeButton = await screen.findByRole('button', { name: /close/i })
    expect(closeButton).toBeInTheDocument()
  })

  it('falls back to aria-label when the header is hidden', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Hidden Title" showHeader={false}>
        <p>Body</p>
      </Modal>
    )
    const dialog = await screen.findByRole('dialog')
    expect(dialog).not.toHaveAttribute('aria-labelledby')
    expect(dialog).toHaveAttribute('aria-label', 'Hidden Title')
  })

  it('forwards an aria-describedby when one is supplied', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Described" describedById="modal-desc">
        <p id="modal-desc">Description text</p>
      </Modal>
    )
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-describedby', 'modal-desc')
  })

  it('Tab from the last focusable element wraps focus back to the first (trap)', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Trap me">
        <input data-testid="first-input" />
        <input data-testid="second-input" />
      </Modal>
    )

    const dialog = await screen.findByRole('dialog')
    const closeBtn = await screen.findByRole('button', { name: /close/i })
    const secondInput = screen.getByTestId('second-input')

    // Drive focus to the last focusable element, then press Tab on the dialog.
    secondInput.focus()
    fireEvent.keyDown(dialog, { key: 'Tab' })
    // Focus must wrap inside the dialog. The first focusable in DOM order is
    // the close button (which sits in the header). Tab from the last element
    // should land focus there — not let the browser tab out of the dialog.
    expect(document.activeElement).toBe(closeBtn)
    expect(dialog.contains(document.activeElement)).toBe(true)
  })

  it('Shift+Tab from the first focusable element wraps to the last (trap)', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Trap shift">
        <input data-testid="only-input" />
      </Modal>
    )
    const dialog = await screen.findByRole('dialog')
    const closeBtn = await screen.findByRole('button', { name: /close/i })
    const onlyInput = screen.getByTestId('only-input')

    closeBtn.focus()
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    // The last focusable in DOM order is the only input, so Shift+Tab from
    // the close button wraps to it.
    expect(document.activeElement).toBe(onlyInput)
  })

  it('restores focus to the trigger element after the modal closes', async () => {
    function Harness() {
      const [open, setOpen] = useState(false)
      return (
        <>
          <button data-testid="trigger" onClick={() => setOpen(true)}>
            Open
          </button>
          <Modal isOpen={open} onClose={() => setOpen(false)} title="Trigger restore">
            <p>Body</p>
          </Modal>
        </>
      )
    }
    render(<Harness />)
    const trigger = screen.getByTestId('trigger')
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    fireEvent.click(trigger)
    await screen.findByRole('dialog')

    // Close via the X button — focus should return to the trigger.
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(document.activeElement).toBe(trigger)
  })
})
