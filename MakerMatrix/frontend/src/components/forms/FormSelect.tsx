import { forwardRef, SelectHTMLAttributes, ReactNode } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import FormField from '../ui/FormField'
import { ChevronDown } from 'lucide-react'

interface FormSelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'> {
  label: string
  registration?: UseFormRegisterReturn
  error?: string
  description?: string
  required?: boolean
  className?: string
  fieldClassName?: string
  placeholder?: string
  children: ReactNode
}

const FormSelect = forwardRef<HTMLSelectElement, FormSelectProps>(
  ({ 
    label, 
    registration, 
    error, 
    description, 
    required, 
    className, 
    fieldClassName,
    placeholder,
    children,
    ...selectProps 
  }, ref) => {
    return (
      <FormField 
        label={label} 
        required={required} 
        error={error} 
        description={description}
        className={className}
      >
        <div className="relative">
          <select
            ref={ref}
            className={`
              w-full px-3 py-2 border border-border rounded-md 
              bg-background text-primary
              focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
              disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed
              appearance-none pr-10
              ${error ? 'border-red-500' : 'border-border'}
              ${fieldClassName || ''}
            `}
            {...registration}
            {...selectProps}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {children}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-secondary pointer-events-none" />
        </div>
      </FormField>
    )
  }
)

FormSelect.displayName = 'FormSelect'

export default FormSelect