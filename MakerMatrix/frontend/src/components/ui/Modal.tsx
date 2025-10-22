import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'

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
}

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
}: ModalProps) => {
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-6xl',
  }

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !loading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, loading, onClose])

  const modalContent = (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] overflow-y-auto">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
          />

          {/* Modal - fade and scale only, no vertical movement */}
          <div className="min-h-screen p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className={`relative w-full ${sizeClasses[size]} mx-auto mt-20 bg-background-secondary border-2 border-purple-500/30 rounded-lg shadow-2xl shadow-purple-500/10 text-primary ${className}`}
              style={{
                boxShadow: '0 25px 50px -12px rgba(168, 85, 247, 0.15), 0 0 0 1px rgba(168, 85, 247, 0.1)',
              }}
            >
              {/* Header */}
              {showHeader && (
                <div className="flex items-center justify-between p-6 border-b border-border">
                  <h2 className="text-xl font-semibold text-primary">{title}</h2>
                  <button
                    onClick={onClose}
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
