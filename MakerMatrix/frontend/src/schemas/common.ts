import { z } from 'zod'

// Common validation rules used across multiple schemas
export const commonValidation = {
  // Required string with minimum length
  requiredString: (fieldName: string, minLength = 1) =>
    z.string()
      .min(minLength, `${fieldName} is required`)
      .trim(),

  // Optional string that can be empty
  optionalString: z.string().optional(),

  // Optional string that trims whitespace and converts empty to undefined
  optionalTrimmedString: z.string()
    .trim()
    .transform(val => val === '' ? undefined : val)
    .optional(),

  // Required email validation
  email: z.string()
    .email('Invalid email format')
    .min(1, 'Email is required'),

  // UUID validation
  uuid: z.string()
    .uuid('Invalid UUID format'),

  // Optional UUID validation
  optionalUuid: z.string()
    .uuid('Invalid UUID format')
    .optional(),

  // Positive integer validation
  positiveInteger: (fieldName: string) =>
    z.number()
      .int(`${fieldName} must be an integer`)
      .min(0, `${fieldName} must be positive`),

  // Required positive integer
  requiredPositiveInteger: (fieldName: string) =>
    z.number()
      .int(`${fieldName} must be an integer`)
      .min(1, `${fieldName} must be greater than 0`),

  // URL validation (optional)
  optionalUrl: z.string()
    .url('Invalid URL format')
    .optional()
    .or(z.literal('')),

  // File upload validation
  file: z.instanceof(File, { message: 'File is required' }),

  // Optional file upload
  optionalFile: z.instanceof(File).optional(),

  // Image file validation
  imageFile: z.instanceof(File)
    .refine(
      (file) => file.type.startsWith('image/'),
      'File must be an image'
    )
    .refine(
      (file) => file.size <= 5 * 1024 * 1024, // 5MB
      'Image must be less than 5MB'
    ),

  // Optional image file
  optionalImageFile: z.instanceof(File)
    .refine(
      (file) => file.type.startsWith('image/'),
      'File must be an image'
    )
    .refine(
      (file) => file.size <= 5 * 1024 * 1024, // 5MB
      'Image must be less than 5MB'
    )
    .optional(),

  // JSON object validation
  jsonObject: z.record(z.any()).default({}),

  // Array of strings validation
  stringArray: z.array(z.string()).default([]),
}

// Common form field constraints
export const fieldConstraints = {
  name: {
    minLength: 1,
    maxLength: 255,
  },
  description: {
    maxLength: 1000,
  },
  partNumber: {
    maxLength: 100,
  },
  supplier: {
    maxLength: 100,
  },
  username: {
    minLength: 3,
    maxLength: 50,
  },
  password: {
    minLength: 8,
    maxLength: 128,
  },
} as const

// Common error messages
export const errorMessages = {
  required: (field: string) => `${field} is required`,
  minLength: (field: string, min: number) => `${field} must be at least ${min} characters`,
  maxLength: (field: string, max: number) => `${field} must be no more than ${max} characters`,
  invalid: (field: string) => `${field} is invalid`,
  positive: (field: string) => `${field} must be positive`,
  integer: (field: string) => `${field} must be a whole number`,
} as const

// Utility function to create consistent validation messages
export const createValidationMessage = (
  type: keyof typeof errorMessages,
  field: string,
  ...args: any[]
): string => {
  const messageFunc = errorMessages[type]
  if (typeof messageFunc === 'function') {
    return messageFunc(field, ...args)
  }
  return messageFunc
}