import { ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'

interface FormFieldProps {
  label: string
  required?: boolean
  error?: string
  children: ReactNode
  description?: string
}

const FormField = ({ label, required, error, children, description }: FormFieldProps) => {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-text-primary">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {description && (
        <p className="text-xs text-text-secondary">{description}</p>
      )}
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