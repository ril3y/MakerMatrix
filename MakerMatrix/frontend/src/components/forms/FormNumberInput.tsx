import { forwardRef, InputHTMLAttributes } from 'react'
import { UseFormRegisterReturn } from 'react-hook-form'
import FormField from '../ui/FormField'

interface FormNumberInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'type'> {
  label: string
  registration?: UseFormRegisterReturn
  error?: string
  description?: string
  required?: boolean
  className?: string
  fieldClassName?: string
  min?: number
  max?: number
  step?: number | string
  allowDecimals?: boolean
}

const FormNumberInput = forwardRef<HTMLInputElement, FormNumberInputProps>(
  (
    {
      label,
      registration,
      error,
      description,
      required,
      className,
      fieldClassName,
      min,
      max,
      step,
      allowDecimals = false,
      ...inputProps
    },
    ref
  ) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!allowDecimals && e.key === '.') {
        e.preventDefault()
      }

      // Allow: backspace, delete, tab, escape, enter, home, end, left, right arrows
      if (
        [46, 8, 9, 27, 13, 110, 35, 36, 37, 39].indexOf(e.keyCode) !== -1 ||
        // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
        (e.keyCode === 65 && e.ctrlKey === true) ||
        (e.keyCode === 67 && e.ctrlKey === true) ||
        (e.keyCode === 86 && e.ctrlKey === true) ||
        (e.keyCode === 88 && e.ctrlKey === true)
      ) {
        return
      }

      // Ensure that it is a number and stop the keypress if not
      if ((e.shiftKey || e.keyCode < 48 || e.keyCode > 57) && (e.keyCode < 96 || e.keyCode > 105)) {
        e.preventDefault()
      }
    }

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
          type="number"
          min={min}
          max={max}
          step={step || (allowDecimals ? 'any' : 1)}
          onKeyDown={handleKeyDown}
          className={`
            w-full px-3 py-2 border border-border rounded-md 
            bg-background text-primary
            focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
            disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed
            [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none
            ${error ? 'border-red-500' : 'border-border'}
            ${fieldClassName || ''}
          `}
          {...registration}
          {...inputProps}
        />
      </FormField>
    )
  }
)

FormNumberInput.displayName = 'FormNumberInput'

export default FormNumberInput
