import { ReactNode, FormEvent } from 'react'
import { Save, X, Plus, Edit3 } from 'lucide-react'
import Modal from './Modal'

interface CrudModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  onSubmit: (e: FormEvent) => void | Promise<void>
  loading?: boolean
  loadingText?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  mode?: 'create' | 'edit' | 'view'
  submitText?: string
  cancelText?: string
  showSubmitButton?: boolean
  showCancelButton?: boolean
  submitButtonIcon?: ReactNode
  disabled?: boolean
  className?: string
  footerContent?: ReactNode
}

const CrudModal = ({
  isOpen,
  onClose,
  title,
  children,
  onSubmit,
  loading = false,
  loadingText,
  size = 'md',
  mode = 'create',
  submitText,
  cancelText = 'Cancel',
  showSubmitButton = true,
  showCancelButton = true,
  submitButtonIcon,
  disabled = false,
  className = '',
  footerContent,
}: CrudModalProps) => {
  // Default submit text based on mode
  const getDefaultSubmitText = () => {
    if (loading && loadingText) return loadingText
    if (loading) {
      switch (mode) {
        case 'create':
          return 'Creating...'
        case 'edit':
          return 'Updating...'
        default:
          return 'Processing...'
      }
    }
    return submitText || (mode === 'create' ? 'Create' : mode === 'edit' ? 'Update' : 'Save')
  }

  // Default icon based on mode
  const getDefaultIcon = () => {
    if (loading) {
      return <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
    }
    if (submitButtonIcon) return submitButtonIcon
    switch (mode) {
      case 'create':
        return <Plus className="w-4 h-4" />
      case 'edit':
        return <Edit3 className="w-4 h-4" />
      default:
        return <Save className="w-4 h-4" />
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await onSubmit(e)
  }

  const handleClose = () => {
    if (loading) return // Prevent closing while loading
    onClose()
  }

  const footer = (
    <div className="flex justify-end gap-3">
      {footerContent}
      {showCancelButton && (
        <button
          type="button"
          onClick={handleClose}
          className="btn btn-secondary"
          disabled={loading}
        >
          {cancelText}
        </button>
      )}
      {showSubmitButton && (
        <button
          type="submit"
          form="crud-modal-form"
          className="btn btn-primary flex items-center gap-2"
          disabled={loading || disabled}
        >
          {getDefaultIcon()}
          {getDefaultSubmitText()}
        </button>
      )}
    </div>
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={title}
      size={size}
      showFooter={true}
      footer={footer}
      loading={loading}
      className={className}
    >
      <form
        id="crud-modal-form"
        data-testid="crud-modal-form"
        onSubmit={handleSubmit}
        className="space-y-6"
      >
        {children}
      </form>
    </Modal>
  )
}

export default CrudModal
