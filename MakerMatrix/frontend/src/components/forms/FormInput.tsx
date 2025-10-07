import { forwardRef, InputHTMLAttributes } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import FormField from '../ui/FormField'

interface FormInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: string
  registration?: UseFormRegisterReturn
  error?: string
  description?: string
  required?: boolean
  className?: string
  fieldClassName?: string
}

const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
  (
    {
      label,
      registration,
      error,
      description,
      required,
      className,
      fieldClassName,
      type = 'text',
      ...inputProps
    },
    ref
  ) => {
    return (
      <FormField
        label={label}
        required={required}
        error={error}
        description={description}
        className={className}
      >
        <input
          ref={ref}
          type={type}
          className={`
            w-full px-3 py-2 border border-theme-primary rounded-md 
            bg-theme-primary text-theme-primary
            focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
            disabled:bg-theme-tertiary disabled:text-theme-muted disabled:cursor-not-allowed
            ${error ? 'border-red-500' : 'border-theme-primary'}
            ${fieldClassName || ''}
          `}
          {...registration}
          {...inputProps}
        />
      </FormField>
    )
  }
)

FormInput.displayName = 'FormInput'

export default FormInput
