import { z } from 'zod'
import { commonValidation, fieldConstraints } from './common'

// Base part schema for common fields
export const basePartSchema = z.object({
  part_name: commonValidation
    .requiredString('Part name')
    .max(
      fieldConstraints.name.maxLength,
      `Part name must be no more than ${fieldConstraints.name.maxLength} characters`
    ),

  part_number: commonValidation.optionalTrimmedString.refine(
    (val) => !val || val.length <= fieldConstraints.partNumber.maxLength,
    `Part number must be no more than ${fieldConstraints.partNumber.maxLength} characters`
  ),

  description: commonValidation.optionalTrimmedString.refine(
    (val) => !val || val.length <= fieldConstraints.description.maxLength,
    `Description must be no more than ${fieldConstraints.description.maxLength} characters`
  ),

  quantity: commonValidation.positiveInteger('Quantity').default(1),

  supplier: commonValidation.optionalTrimmedString.refine(
    (val) => !val || val.length <= fieldConstraints.supplier.maxLength,
    `Supplier must be no more than ${fieldConstraints.supplier.maxLength} characters`
  ),

  location_id: commonValidation.optionalUuid,

  image_url: commonValidation.optionalUrl,

  additional_properties: commonValidation.jsonObject,

  category_names: commonValidation.stringArray,
})

// Schema for creating a new part
export const createPartSchema = basePartSchema.extend({
  // Add any create-specific validation
  part_name: commonValidation
    .requiredString('Part name')
    .min(
      fieldConstraints.name.minLength,
      `Part name must be at least ${fieldConstraints.name.minLength} character`
    )
    .max(
      fieldConstraints.name.maxLength,
      `Part name must be no more than ${fieldConstraints.name.maxLength} characters`
    ),
})

// Schema for updating an existing part
export const updatePartSchema = basePartSchema.partial().extend({
  // Part name is still required for updates
  part_name: commonValidation
    .requiredString('Part name')
    .min(
      fieldConstraints.name.minLength,
      `Part name must be at least ${fieldConstraints.name.minLength} character`
    )
    .max(
      fieldConstraints.name.maxLength,
      `Part name must be no more than ${fieldConstraints.name.maxLength} characters`
    ),
})

// Schema for part search
export const partSearchSchema = z
  .object({
    search_term: commonValidation.optionalTrimmedString,
    min_quantity: z.number().int().min(0).optional(),
    max_quantity: z.number().int().min(0).optional(),
    category_names: commonValidation.stringArray,
    location_id: commonValidation.optionalUuid,
    supplier: commonValidation.optionalTrimmedString,
    sort_by: z.enum(['part_name', 'part_number', 'quantity', 'location']).default('part_name'),
    sort_order: z.enum(['asc', 'desc']).default('asc'),
    page: z.number().int().min(1).default(1),
    page_size: z.number().int().min(1).max(100).default(10),
  })
  .refine(
    (data) => {
      if (data.min_quantity !== undefined && data.max_quantity !== undefined) {
        return data.min_quantity <= data.max_quantity
      }
      return true
    },
    {
      message: 'Maximum quantity must be greater than or equal to minimum quantity',
      path: ['max_quantity'],
    }
  )

// Schema for part form with image upload
export const partFormSchema = createPartSchema.extend({
  image_file: commonValidation.optionalImageFile,
})

// Schema for updating part form with image upload
export const updatePartFormSchema = updatePartSchema.extend({
  image_file: commonValidation.optionalImageFile,
})

// Schema for part enrichment
export const partEnrichmentSchema = z.object({
  part_id: commonValidation.uuid,
  supplier: commonValidation.requiredString('Supplier'),
  capabilities: z.array(z.string()).min(1, 'At least one capability must be selected'),
})

// Schema for bulk part operations
export const bulkPartOperationSchema = z.object({
  part_ids: z.array(commonValidation.uuid).min(1, 'At least one part must be selected'),
  operation: z.enum(['delete', 'update_location', 'update_categories', 'enrich']),
  data: z.record(z.any()).optional(),
})

// Additional properties schema for dynamic fields
export const additionalPropertySchema = z.object({
  key: commonValidation
    .requiredString('Property name')
    .max(100, 'Property name must be no more than 100 characters')
    .refine(
      (val) => /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(val),
      'Property name must start with a letter or underscore and contain only letters, numbers, and underscores'
    ),
  value: z.union([z.string(), z.number(), z.boolean()]),
  type: z.enum(['string', 'number', 'boolean']).default('string'),
})

// Type exports for TypeScript
export type BasePartData = z.infer<typeof basePartSchema>
export type CreatePartData = z.infer<typeof createPartSchema>
export type UpdatePartData = z.infer<typeof updatePartSchema>
export type PartSearchData = z.infer<typeof partSearchSchema>
export type PartFormData = z.infer<typeof partFormSchema>
export type UpdatePartFormData = z.infer<typeof updatePartFormSchema>
export type PartEnrichmentData = z.infer<typeof partEnrichmentSchema>
export type BulkPartOperationData = z.infer<typeof bulkPartOperationSchema>
export type AdditionalPropertyData = z.infer<typeof additionalPropertySchema>
