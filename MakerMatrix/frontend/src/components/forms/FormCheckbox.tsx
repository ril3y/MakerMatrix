import { forwardRef, InputHTMLAttributes } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import { Check } from 'lucide-react'

interface FormCheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'type'> {
  label: string
  registration?: UseFormRegisterReturn
  error?: string
  description?: string
  className?: string
  fieldClassName?: string
}

const FormCheckbox = forwardRef<HTMLInputElement, FormCheckboxProps>(
  ({ label, registration, error, description, className, fieldClassName, ...inputProps }, ref) => {
    return (
      <div className={`space-y-2 ${className || ''}`}>
        <div className="flex items-start space-x-2">
          <div className="relative flex items-center">
            <input
              ref={ref}
              type="checkbox"
              className={`
                sr-only peer
                ${fieldClassName || ''}
              `}
              {...registration}
              {...inputProps}
            />
            <div
              className="
              w-4 h-4 border border-border rounded 
              bg-background 
              peer-checked:bg-accent peer-checked:border-accent
              peer-focus:ring-2 peer-focus:ring-accent peer-focus:ring-offset-2
              peer-disabled:bg-muted peer-disabled:border-muted-foreground/50 peer-disabled:cursor-not-allowed
              flex items-center justify-center
              transition-colors duration-200
            "
            >
              <Check className="w-3 h-3 text-white opacity-0 peer-checked:opacity-100 transition-opacity duration-200" />
            </div>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-primary cursor-pointer">{label}</label>
            {description && <p className="text-xs text-secondary">{description}</p>}
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-1 text-red-500 text-sm ml-6">
            <span>{error}</span>
          </div>
        )}
      </div>
    )
  }
)

FormCheckbox.displayName = 'FormCheckbox'

export default FormCheckbox
