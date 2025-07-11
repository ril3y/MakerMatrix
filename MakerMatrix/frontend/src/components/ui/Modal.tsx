import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { ReactNode } from 'react'

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
  className = ''
}: ModalProps) => {
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            />

            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className={`relative w-full ${sizeClasses[size]} bg-background-primary border border-border rounded-lg shadow-xl text-primary ${className}`}
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
}

export default Modal