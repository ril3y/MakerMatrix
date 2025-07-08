import { z } from 'zod'
import { commonValidation, fieldConstraints } from './common'

// Base location schema for common fields
export const baseLocationSchema = z.object({
  name: commonValidation.requiredString('Location name')
    .min(fieldConstraints.name.minLength, `Location name must be at least ${fieldConstraints.name.minLength} character`)
    .max(fieldConstraints.name.maxLength, `Location name must be no more than ${fieldConstraints.name.maxLength} characters`),
  
  description: commonValidation.optionalTrimmedString
    .refine(
      (val) => !val || val.length <= fieldConstraints.description.maxLength,
      `Description must be no more than ${fieldConstraints.description.maxLength} characters`
    ),
  
  parent_id: commonValidation.optionalUuid,
  
  location_type: z.enum(['standard', 'warehouse', 'shelf', 'bin', 'drawer', 'cabinet', 'room', 'building'])
    .default('standard'),
  
  image_url: commonValidation.optionalUrl,
})

// Schema for creating a new location
export const createLocationSchema = baseLocationSchema.extend({
  // Add any create-specific validation
})

// Schema for updating an existing location
const baseUpdateLocationSchema = baseLocationSchema.partial().extend({
  // Location name is still required for updates
  name: commonValidation.requiredString('Location name')
    .min(fieldConstraints.name.minLength, `Location name must be at least ${fieldConstraints.name.minLength} character`)
    .max(fieldConstraints.name.maxLength, `Location name must be no more than ${fieldConstraints.name.maxLength} characters`),
})

export const updateLocationSchema = baseUpdateLocationSchema.refine(
  (data) => {
    // Prevent setting parent_id to self (when updating)
    if (data.parent_id && data.parent_id === (data as any).id) {
      return false
    }
    return true
  },
  {
    message: 'A location cannot be its own parent',
    path: ['parent_id'],
  }
)

// Schema for location form with image upload
export const locationFormSchema = createLocationSchema.extend({
  image_file: commonValidation.optionalImageFile,
  emoji: z.string()
    .optional()
    .refine(
      (val) => !val || /^[\u{1F300}-\u{1F9FF}]$/u.test(val),
      'Must be a valid emoji'
    ),
})

// Schema for updating location form with image upload
export const updateLocationFormSchema = baseUpdateLocationSchema.extend({
  image_file: commonValidation.optionalImageFile,
  emoji: z.string()
    .optional()
    .refine(
      (val) => !val || /^[\u{1F300}-\u{1F9FF}]$/u.test(val),
      'Must be a valid emoji'
    ),
}).refine(
  (data) => {
    // Prevent setting parent_id to self (when updating)
    if (data.parent_id && data.parent_id === (data as any).id) {
      return false
    }
    return true
  },
  {
    message: 'A location cannot be its own parent',
    path: ['parent_id'],
  }
)

// Schema for location search and filtering
export const locationSearchSchema = z.object({
  search_term: commonValidation.optionalTrimmedString,
  parent_id: commonValidation.optionalUuid,
  location_type: z.enum(['standard', 'warehouse', 'shelf', 'bin', 'drawer', 'cabinet', 'room', 'building']).optional(),
  has_parts: z.boolean().optional(),
  include_children: z.boolean().default(true),
})

// Schema for moving parts between locations
export const movePartsSchema = z.object({
  part_ids: z.array(commonValidation.uuid).min(1, 'At least one part must be selected'),
  target_location_id: commonValidation.optionalUuid,
})

// Schema for location hierarchy operations
export const locationHierarchySchema = z.object({
  location_id: commonValidation.uuid,
  new_parent_id: commonValidation.optionalUuid,
}).refine(
  (data) => {
    // Prevent setting parent to self
    if (data.new_parent_id === data.location_id) {
      return false
    }
    return true
  },
  {
    message: 'A location cannot be moved to itself',
    path: ['new_parent_id'],
  }
)

// Schema for bulk location operations
export const bulkLocationOperationSchema = z.object({
  location_ids: z.array(commonValidation.uuid).min(1, 'At least one location must be selected'),
  operation: z.enum(['delete', 'move', 'change_type']),
  data: z.record(z.any()).optional(),
})

// Schema for location path display
export const locationPathSchema = z.object({
  location_id: commonValidation.uuid,
  include_self: z.boolean().default(true),
  separator: z.string().default(' > '),
})

// Validation helpers for location-specific rules
export const locationValidationRules = {
  // Check if location name is unique within the same parent
  uniqueNameInParent: (name: string, parentId?: string, excludeId?: string) => {
    return z.string().refine(
      async (value) => {
        // This would typically make an API call to check uniqueness
        // For now, we'll just validate the format
        return value.trim().length > 0
      },
      'Location name must be unique within the same parent location'
    )
  },

  // Validate location hierarchy depth (prevent too deep nesting)
  maxHierarchyDepth: (currentDepth: number, maxDepth = 10) => {
    return z.string().refine(
      () => currentDepth < maxDepth,
      `Location hierarchy cannot exceed ${maxDepth} levels`
    )
  },

  // Validate that parent location exists and is not a descendant
  validParent: (locationId?: string) => {
    return commonValidation.optionalUuid.refine(
      async (parentId) => {
        if (!parentId) return true
        // This would typically make an API call to validate parent
        // For now, we'll just check it's not the same as current location
        return parentId !== locationId
      },
      'Invalid parent location selected'
    )
  },
}

// Type exports for TypeScript
export type BaseLocationData = z.infer<typeof baseLocationSchema>
export type CreateLocationData = z.infer<typeof createLocationSchema>
export type UpdateLocationData = z.infer<typeof updateLocationSchema>
export type LocationFormData = z.infer<typeof locationFormSchema>
export type UpdateLocationFormData = z.infer<typeof updateLocationFormSchema>
export type LocationSearchData = z.infer<typeof locationSearchSchema>
export type MovePartsData = z.infer<typeof movePartsSchema>
export type LocationHierarchyData = z.infer<typeof locationHierarchySchema>
export type BulkLocationOperationData = z.infer<typeof bulkLocationOperationSchema>
export type LocationPathData = z.infer<typeof locationPathSchema>