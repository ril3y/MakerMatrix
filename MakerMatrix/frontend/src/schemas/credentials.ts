import { z } from 'zod'
import { commonValidation } from './common'

// Base credential field interface for form validation
export const credentialFieldSchema = z.object({
  name: z.string().min(1, 'Field name is required'),
  label: z.string().min(1, 'Field label is required'),
  field_type: z.enum(['text', 'password', 'url', 'email']),
  required: z.boolean(),
  description: z.string().optional(),
  placeholder: z.string().optional(),
  help_text: z.string().optional(),
})

// Dynamic credential form schema - will be generated based on credential fields
export const createCredentialFormSchema = (
  fields: Array<{
    name: string
    label: string
    field_type: string
    required: boolean
    description?: string
    placeholder?: string
    help_text?: string
  }>
) => {
  const schemaFields: Record<string, z.ZodTypeAny> = {}

  fields.forEach((field) => {
    let fieldSchema: z.ZodTypeAny

    switch (field.field_type) {
      case 'email':
        fieldSchema = z.string().email('Invalid email format')
        break
      case 'url':
        fieldSchema = z.string().url('Invalid URL format')
        break
      case 'password':
      case 'text':
      default:
        fieldSchema = z.string()
        break
    }

    // Apply required validation
    if (field.required) {
      fieldSchema = fieldSchema.min(1, `${field.label} is required`)
    } else {
      fieldSchema = fieldSchema.optional().or(z.literal(''))
    }

    schemaFields[field.name] = fieldSchema
  })

  return z.object(schemaFields)
}

// Test result schema
export const credentialTestResultSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
})

// Credential status schema
export const credentialStatusSchema = z.object({
  fully_configured: z.boolean(),
  has_database_credentials: z.boolean(),
  has_environment_credentials: z.boolean(),
  configured_fields: z.array(z.string()).optional(),
  missing_required: z.array(z.string()).optional(),
  error: z.string().optional(),
})

// Types
export type CredentialField = z.infer<typeof credentialFieldSchema>
export type CredentialFormData = Record<string, string>
export type CredentialTestResult = z.infer<typeof credentialTestResultSchema>
export type CredentialStatus = z.infer<typeof credentialStatusSchema>
