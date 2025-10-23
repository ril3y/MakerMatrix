import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'

interface UseModalFormProps<T> {
  initialData: T
  validate?: (data: T) => Record<string, string>
  onSubmit: (data: T) => Promise<void>
  onSuccess?: () => void
  successMessage?: string
  resetOnClose?: boolean
}

interface UseModalFormReturn<T> {
  formData: T
  setFormData: React.Dispatch<React.SetStateAction<T>>
  errors: Record<string, string>
  setErrors: React.Dispatch<React.SetStateAction<Record<string, string>>>
  loading: boolean
  setLoading: React.Dispatch<React.SetStateAction<boolean>>
  handleSubmit: (e: React.FormEvent) => Promise<void>
  handleClose: (onClose: () => void) => void
  updateField: <K extends keyof T>(field: K, value: T[K]) => void
  isValid: boolean
  hasChanges: boolean
  resetForm: () => void
}

export const useModalForm = <T extends Record<string, unknown>>({
  initialData,
  validate,
  onSubmit,
  onSuccess,
  successMessage,
  resetOnClose = true,
}: UseModalFormProps<T>): UseModalFormReturn<T> => {
  const [formData, setFormData] = useState<T>(initialData)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [originalData] = useState<T>(structuredClone(initialData))

  // Reset form data when initialData changes
  useEffect(() => {
    setFormData(initialData)
  }, [initialData])

  const resetForm = useCallback(() => {
    setFormData(initialData)
    setErrors({})
    setLoading(false)
  }, [initialData])

  const updateField = useCallback(
    <K extends keyof T>(field: K, value: T[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }))
      // Clear error for this field when user starts typing
      if (errors[field as string]) {
        setErrors((prev) => {
          const newErrors = { ...prev }
          delete newErrors[field as string]
          return newErrors
        })
      }
    },
    [errors]
  )

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()

      // Run validation if provided
      if (validate) {
        const validationErrors = validate(formData)
        setErrors(validationErrors)
        if (Object.keys(validationErrors).length > 0) {
          return
        }
      }

      try {
        setLoading(true)
        await onSubmit(formData)

        if (successMessage) {
          toast.success(successMessage)
        }

        if (onSuccess) {
          onSuccess()
        }
      } catch (error) {
        const err = error as {
          response?: { data?: { message?: string; errors?: Record<string, string> } }
          message?: string
        }
        const errorMessage = err.response?.data?.message || err.message || 'An error occurred'
        toast.error(errorMessage)

        // If server returns field-specific errors, set them
        if (err.response?.data?.errors) {
          setErrors(err.response.data.errors)
        }
      } finally {
        setLoading(false)
      }
    },
    [formData, validate, onSubmit, onSuccess, successMessage]
  )

  const handleClose = useCallback(
    (onClose: () => void) => {
      if (loading) return // Prevent closing while loading

      if (resetOnClose) {
        resetForm()
      }
      onClose()
    },
    [loading, resetOnClose, resetForm]
  )

  // Check if form is valid (no errors and required fields filled)
  const isValid = Object.keys(errors).length === 0

  // Check if form has changes from original data
  const hasChanges = JSON.stringify(formData) !== JSON.stringify(originalData)

  return {
    formData,
    setFormData,
    errors,
    setErrors,
    loading,
    setLoading,
    handleSubmit,
    handleClose,
    updateField,
    isValid,
    hasChanges,
    resetForm,
  }
}
