import React, { useState, useCallback } from 'react'
import type {
  UseFormProps,
  FieldValues,
  Path,
  RegisterOptions,
  SetValueConfig,
} from 'react-hook-form'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { z } from 'zod'
import { toast } from 'react-hot-toast'

interface UseFormWithValidationOptions<T extends FieldValues> extends UseFormProps<T> {
  schema: z.ZodSchema<T>
  onSubmit: (data: T) => Promise<unknown> | void
  onSuccess?: (data: unknown) => void
  onError?: (error: unknown) => void
  successMessage?: string
  resetOnSuccess?: boolean
  transformData?: (data: T) => unknown
}

export const useFormWithValidation = <T extends FieldValues>({
  schema,
  onSubmit,
  onSuccess,
  onError,
  successMessage,
  resetOnSuccess = false,
  transformData,
  ...formOptions
}: UseFormWithValidationOptions<T>) => {
  const [loading, setLoading] = useState(false)

  const form = useForm<T>({
    resolver: zodResolver(schema),
    mode: 'onChange',
    ...formOptions,
  })

  const {
    handleSubmit,
    reset: formReset,
    formState: { errors, isValid, isDirty },
  } = form

  const onSubmitHandler = useCallback(
    async (data: T) => {
      try {
        setLoading(true)

        // Transform data if transformer is provided
        const submitData = transformData ? transformData(data) : data

        // Call the submit function
        const result = await onSubmit(submitData)

        // Handle success
        if (successMessage) {
          toast.success(successMessage)
        }

        if (resetOnSuccess) {
          formReset()
        }

        onSuccess?.(result)

        return result
      } catch (error) {
        console.error('Form submission error:', error)

        const err = error as {
          response?: {
            status?: number
            data?: { detail?: unknown; message?: string }
          }
          message?: string
        }

        // Handle validation errors from server
        if (err.response?.status === 422) {
          const validationErrors = err.response.data.detail
          if (Array.isArray(validationErrors)) {
            validationErrors.forEach((validationError: unknown) => {
              const ve = validationError as { loc?: unknown[]; msg?: string }
              if (ve.loc && ve.msg) {
                const field = ve.loc[ve.loc.length - 1] as Path<T>
                form.setError(field, { message: ve.msg })
              }
            })
          }
        } else {
          // Handle general errors
          const errorMessage = err.response?.data?.message || err.message || 'An error occurred'
          toast.error(errorMessage)
        }

        onError?.(error)
        throw error
      } finally {
        setLoading(false)
      }
    },
    [onSubmit, onSuccess, onError, successMessage, resetOnSuccess, transformData, formReset, form]
  )

  // Enhanced field registration with better error handling
  const register = useCallback(
    (name: Path<T>, options?: RegisterOptions<T>) => {
      return form.register(name, options)
    },
    [form]
  )

  // Get field error message
  const getFieldError = useCallback(
    (name: Path<T>) => {
      return errors[name]?.message as string | undefined
    },
    [errors]
  )

  // Check if field has error
  const hasFieldError = useCallback(
    (name: Path<T>) => {
      return !!errors[name]
    },
    [errors]
  )

  // Get field props for easier component integration
  const getFieldProps = useCallback(
    (name: Path<T>) => {
      return {
        registration: register(name),
        error: getFieldError(name),
      }
    },
    [register, getFieldError]
  )

  // Reset specific field
  const resetField = useCallback(
    (name: Path<T>) => {
      form.resetField(name)
    },
    [form]
  )

  // Set field value programmatically
  const setValue = useCallback(
    (name: Path<T>, value: unknown, options?: SetValueConfig) => {
      form.setValue(name, value, options)
    },
    [form]
  )

  // Get field value
  const getValue = useCallback(
    (name: Path<T>) => {
      return form.getValues(name)
    },
    [form]
  )

  // Watch field changes
  const watch = useCallback(
    (name?: Path<T> | Path<T>[]) => {
      return form.watch(name)
    },
    [form]
  )

  // Trigger field validation
  const trigger = useCallback(
    (name?: Path<T> | Path<T>[]) => {
      return form.trigger(name)
    },
    [form]
  )

  return {
    // Form methods
    ...form,

    // Custom methods
    onSubmit: handleSubmit(onSubmitHandler),
    register,
    getFieldError,
    hasFieldError,
    getFieldProps,
    resetField,
    setValue,
    getValue,
    watch,
    trigger,

    // State
    loading,
    isValid,
    isDirty,
    errors,

    // Utilities
    reset: () => {
      formReset()
      setLoading(false)
    },
  }
}

// Convenience hook for modal forms that combines with existing useModalForm pattern
export const useModalFormWithValidation = <T extends FieldValues>(
  options: UseFormWithValidationOptions<T> & {
    isOpen: boolean
    onClose: () => void
    resetOnClose?: boolean
  }
) => {
  const { isOpen, onClose, resetOnClose = true, ...formOptions } = options

  const form = useFormWithValidation({
    ...formOptions,
    onSuccess: (data) => {
      formOptions.onSuccess?.(data)
      onClose()
    },
  })

  // Reset form when modal closes
  React.useEffect(() => {
    if (!isOpen && resetOnClose) {
      form.reset()
    }
  }, [isOpen, resetOnClose]) // Don't include form.reset - it's stable from the hook

  return {
    ...form,
    isOpen,
    onClose,
  }
}

export default useFormWithValidation
