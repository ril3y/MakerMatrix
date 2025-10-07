import { forwardRef, TextareaHTMLAttributes } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import FormField from '../ui/FormField'

interface FormTextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> {
  label: string
  registration?: UseFormRegisterReturn
  error?: string
  description?: string
  required?: boolean
  className?: string
  fieldClassName?: string
  rows?: number
}

const FormTextarea = forwardRef<HTMLTextAreaElement, FormTextareaProps>(
  (
    {
      label,
      registration,
      error,
      description,
      required,
      className,
      fieldClassName,
      rows = 3,
      ...textareaProps
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
        <textarea
          ref={ref}
          rows={rows}
          className={`
            w-full px-3 py-2 border border-border rounded-md 
            bg-background text-primary
            focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
            disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed
            resize-vertical
            ${error ? 'border-red-500' : 'border-border'}
            ${fieldClassName || ''}
          `}
          {...registration}
          {...textareaProps}
        />
      </FormField>
    )
  }
)

FormTextarea.displayName = 'FormTextarea'

export default FormTextarea
