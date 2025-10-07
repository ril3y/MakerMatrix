import type { ReactNode } from 'react'

interface FormActionsProps {
  onSubmit?: () => void
  onCancel?: () => void
  onReset?: () => void
  submitText?: string
  cancelText?: string
  resetText?: string
  loading?: boolean
  disabled?: boolean
  className?: string
  children?: ReactNode
  submitVariant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  cancelVariant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  resetVariant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  layout?: 'left' | 'right' | 'center' | 'between'
}

const FormActions = ({
  onSubmit,
  onCancel,
  onReset,
  submitText = 'Submit',
  cancelText = 'Cancel',
  resetText = 'Reset',
  loading = false,
  disabled = false,
  className,
  children,
  submitVariant = 'primary',
  cancelVariant = 'outline',
  resetVariant = 'ghost',
  layout = 'right',
}: FormActionsProps) => {
  const layoutClass = {
    left: 'justify-start',
    right: 'justify-end',
    center: 'justify-center',
    between: 'justify-between',
  }

  return (
    <div
      className={`
      flex items-center gap-3 pt-4 mt-6 border-t border-border
      ${layoutClass[layout]}
      ${className || ''}
    `}
    >
      {/* Left side (reset button if layout is between) */}
      {layout === 'between' && onReset && (
        <button
          type="button"
          className={`btn btn-${resetVariant}`}
          onClick={onReset}
          disabled={loading || disabled}
        >
          {resetText}
        </button>
      )}

      {/* Custom children */}
      {children}

      {/* Main action buttons */}
      <div className="flex items-center gap-3">
        {/* Reset button (not in between layout) */}
        {layout !== 'between' && onReset && (
          <button
            type="button"
            className={`btn btn-${resetVariant}`}
            onClick={onReset}
            disabled={loading || disabled}
          >
            {resetText}
          </button>
        )}

        {/* Cancel button */}
        {onCancel && (
          <button
            type="button"
            className={`btn btn-${cancelVariant}`}
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText}
          </button>
        )}

        {/* Submit button */}
        {onSubmit && (
          <button
            type="submit"
            className={`btn btn-${submitVariant} ${loading ? 'loading' : ''}`}
            onClick={onSubmit}
            disabled={loading || disabled}
          >
            {loading ? 'Loading...' : submitText}
          </button>
        )}
      </div>
    </div>
  )
}

export default FormActions
