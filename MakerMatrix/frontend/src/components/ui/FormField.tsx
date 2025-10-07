import type { ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'

interface FormFieldProps {
  label: string
  required?: boolean
  error?: string
  children: ReactNode
  description?: string
  className?: string
}

const FormField = ({
  label,
  required,
  error,
  children,
  description,
  className,
}: FormFieldProps) => {
  return (
    <div className={`space-y-2 ${className || ''}`}>
      <label className="block text-sm font-medium text-theme-primary">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {description && <p className="text-xs text-theme-secondary">{description}</p>}
      {error && (
        <div className="flex items-center gap-1 text-red-500 text-sm">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}

export default FormField
