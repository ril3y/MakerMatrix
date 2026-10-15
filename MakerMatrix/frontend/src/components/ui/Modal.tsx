import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from 'react'
import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useEscapeStack } from '@/hooks/useEscapeStack'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showHeader?: boolean
  showFooter?: boolean
  footer?: ReactNode
  loading?: boolean
  className?: string
  /**
   * Optional id of the element that describes the modal contents. When set,
   * the dialog announces this element via aria-describedby.
   */
  describedById?: string
}

// Selector for all natively focusable elements; matches react-focus-lock's set.
const FOCUSABLE_SELECTOR =
  'a[href], area[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]'

const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showHeader = true,
  showFooter = false,
  footer,
  loading = false,
  className = '',
  describedById,
}: ModalProps) => {
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-6xl',
  }

  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement | null>(null)
  // Element that had focus before the modal opened — restored on unmount.
  const previouslyFocusedRef = useRef<HTMLElement | null>(null)

  // Handle Escape key via shared stack — only topmost modal closes
  useEscapeStack(isOpen, onClose, loading)

  // Focus management: capture the previously-focused element when the modal
  // opens, move focus inside, and restore focus on close.
  useEffect(() => {
    if (!isOpen) return

    previouslyFocusedRef.current = (document.activeElement as HTMLElement | null) ?? null

    // Defer to next tick so the portal is mounted before we query focusables.
    const focusFrame = requestAnimationFrame(() => {
      const dialog = dialogRef.current
      if (!dialog) return
      const focusables = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      const first = focusables[0]
      if (first) {
        first.focus()
      } else {
        // Fall back to focusing the dialog itself (tabindex=-1 set below).
        dialog.focus()
      }
    })

    return () => {
      cancelAnimationFrame(focusFrame)
      // Restore focus to whatever was focused before the modal opened, if it
      // is still in the DOM and focusable.
      const previouslyFocused = previouslyFocusedRef.current
      if (previouslyFocused && document.body.contains(previouslyFocused)) {
        previouslyFocused.focus()
      }
    }
  }, [isOpen])

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab') return
    const dialog = dialogRef.current
    if (!dialog) return
    // Filter only by disabled state — jsdom doesn't compute layout, so
    // `offsetParent` is always null in unit tests. The dialog itself is the
    // only container, so anything that matches the selector here is
    // reachable in practice.
    const focusables = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
      (el) => !el.hasAttribute('disabled')
    )
    if (focusables.length === 0) {
      event.preventDefault()
      dialog.focus()
      return
    }
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    const active = document.activeElement as HTMLElement | null

    if (event.shiftKey) {
      if (active === first || !dialog.contains(active)) {
        event.preventDefault()
        last.focus()
      }
    } else {
      if (active === last || !dialog.contains(active)) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] overflow-y-auto">
          {/* Backdrop — role=presentation since it's a decorative dismiss target.
              Keyboard users dismiss via Esc (useEscapeStack); pointer users click. */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            role="presentation"
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal - fade and scale only, no vertical movement */}
          <div className="min-h-screen p-4">
            <motion.div
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-labelledby={showHeader ? titleId : undefined}
              aria-label={!showHeader ? title : undefined}
              aria-describedby={describedById}
              tabIndex={-1}
              onKeyDown={handleKeyDown}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className={`relative w-full ${sizeClasses[size]} mx-auto mt-20 bg-background-secondary border-2 border-purple-500/30 rounded-lg shadow-2xl shadow-purple-500/10 text-primary ${className}`}
              style={{
                boxShadow:
                  '0 25px 50px -12px rgba(168, 85, 247, 0.15), 0 0 0 1px rgba(168, 85, 247, 0.1)',
              }}
            >
              {/* Header */}
              {showHeader && (
                <div className="flex items-center justify-between p-6 border-b border-border">
                  <h2 id={titleId} className="text-xl font-semibold text-primary">
                    {title}
                  </h2>
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close"
                    className="p-1 rounded-md hover:bg-background-secondary transition-colors"
                    disabled={loading}
                  >
                    <X className="w-5 h-5 text-secondary" />
                  </button>
                </div>
              )}

              {/* Content */}
              <div className={`${showHeader ? 'p-6' : 'p-6 pt-8'} ${showFooter ? 'pb-0' : ''}`}>
                {children}
              </div>

              {/* Footer */}
              {showFooter && footer && (
                <div className="px-6 py-4 border-t border-border bg-background-secondary">
                  {footer}
                </div>
              )}
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  )

  // Render modal at document.body level using portal to escape any parent stacking contexts
  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null
}

export default Modal
