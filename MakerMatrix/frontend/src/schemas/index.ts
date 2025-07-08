// Re-export all schemas for easy importing
export * from './common'
export * from './parts'
export * from './locations'
export * from './categories'
export * from './auth'
export * from './credentials'

// Additional schemas can be added here as they are created
// export * from './suppliers'
// export * from './tasks'
// export * from './settings'

// Utility type for form validation errors
export type FormErrors<T> = Partial<Record<keyof T, string>>

// Generic form state type
export type FormState<T> = {
  data: T
  errors: FormErrors<T>
  loading: boolean
  touched: Partial<Record<keyof T, boolean>>
}

// Form submission result type
export type FormSubmissionResult<T = any> = {
  success: boolean
  data?: T
  errors?: FormErrors<any>
  message?: string
}