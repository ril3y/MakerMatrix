import { z } from 'zod'
import { commonValidation, fieldConstraints } from './common'

// Base category schema for common fields
export const baseCategorySchema = z.object({
  name: commonValidation
    .requiredString('Category name')
    .min(
      fieldConstraints.name.minLength,
      `Category name must be at least ${fieldConstraints.name.minLength} character`
    )
    .max(
      fieldConstraints.name.maxLength,
      `Category name must be no more than ${fieldConstraints.name.maxLength} characters`
    )
    .refine(
      (val) => /^[a-zA-Z0-9\s\-_.()]+$/.test(val),
      'Category name can only contain letters, numbers, spaces, hyphens, underscores, periods, and parentheses'
    ),

  description: commonValidation.optionalTrimmedString.refine(
    (val) => !val || val.length <= fieldConstraints.description.maxLength,
    `Description must be no more than ${fieldConstraints.description.maxLength} characters`
  ),

  parent_id: commonValidation.optionalUuid,
})

// Schema for creating a new category
export const createCategorySchema = baseCategorySchema.extend({
  // Add any create-specific validation
})

// Schema for updating an existing category
export const updateCategorySchema = baseCategorySchema
  .partial()
  .extend({
    // Category name is still required for updates
    name: commonValidation
      .requiredString('Category name')
      .min(
        fieldConstraints.name.minLength,
        `Category name must be at least ${fieldConstraints.name.minLength} character`
      )
      .max(
        fieldConstraints.name.maxLength,
        `Category name must be no more than ${fieldConstraints.name.maxLength} characters`
      )
      .refine(
        (val) => /^[a-zA-Z0-9\s\-_.()]+$/.test(val),
        'Category name can only contain letters, numbers, spaces, hyphens, underscores, periods, and parentheses'
      ),
  })
  .refine(
    (data) => {
      // Prevent setting parent_id to self (when updating)
      if (data.parent_id && data.parent_id === (data as any).id) {
        return false
      }
      return true
    },
    {
      message: 'A category cannot be its own parent',
      path: ['parent_id'],
    }
  )

// Schema for category search and filtering
export const categorySearchSchema = z
  .object({
    search_term: commonValidation.optionalTrimmedString,
    parent_id: commonValidation.optionalUuid,
    has_parts: z.boolean().optional(),
    include_children: z.boolean().default(true),
    min_part_count: z.number().int().min(0).optional(),
    max_part_count: z.number().int().min(0).optional(),
  })
  .refine(
    (data) => {
      if (data.min_part_count !== undefined && data.max_part_count !== undefined) {
        return data.min_part_count <= data.max_part_count
      }
      return true
    },
    {
      message: 'Maximum part count must be greater than or equal to minimum part count',
      path: ['max_part_count'],
    }
  )

// Schema for category hierarchy operations
export const categoryHierarchySchema = z
  .object({
    category_id: commonValidation.uuid,
    new_parent_id: commonValidation.optionalUuid,
  })
  .refine(
    (data) => {
      // Prevent setting parent to self
      if (data.new_parent_id === data.category_id) {
        return false
      }
      return true
    },
    {
      message: 'A category cannot be moved to itself',
      path: ['new_parent_id'],
    }
  )

// Schema for bulk category operations
export const bulkCategoryOperationSchema = z.object({
  category_ids: z.array(commonValidation.uuid).min(1, 'At least one category must be selected'),
  operation: z.enum(['delete', 'move', 'merge']),
  data: z.record(z.any()).optional(),
})

// Schema for category assignment to parts
export const assignCategoriesSchema = z.object({
  part_ids: z.array(commonValidation.uuid).min(1, 'At least one part must be selected'),
  category_ids: z.array(commonValidation.uuid).min(1, 'At least one category must be selected'),
  operation: z.enum(['add', 'remove', 'replace']).default('add'),
})

// Schema for category merge operation
export const mergeCategoriesSchema = z
  .object({
    source_category_ids: z
      .array(commonValidation.uuid)
      .min(1, 'At least one source category must be selected'),
    target_category_id: commonValidation.uuid,
    delete_empty_sources: z.boolean().default(true),
  })
  .refine(
    (data) => {
      // Ensure target is not in source list
      return !data.source_category_ids.includes(data.target_category_id)
    },
    {
      message: 'Target category cannot be one of the source categories',
      path: ['target_category_id'],
    }
  )

// Schema for category path display
export const categoryPathSchema = z.object({
  category_id: commonValidation.uuid,
  include_self: z.boolean().default(true),
  separator: z.string().default(' > '),
})

// Schema for category statistics
export const categoryStatsSchema = z.object({
  category_id: commonValidation.uuid,
  include_children: z.boolean().default(true),
  date_range: z
    .object({
      start_date: z.string().datetime().optional(),
      end_date: z.string().datetime().optional(),
    })
    .optional(),
})

// Validation helpers for category-specific rules
export const categoryValidationRules = {
  // Check if category name is unique (case-insensitive)
  uniqueName: (name: string, excludeId?: string) => {
    return z.string().refine(async (value) => {
      // This would typically make an API call to check uniqueness
      // For now, we'll just validate the format
      const normalized = value.trim().toLowerCase()
      return normalized.length > 0
    }, 'Category name must be unique')
  },

  // Validate category hierarchy depth (prevent too deep nesting)
  maxHierarchyDepth: (currentDepth: number, maxDepth = 5) => {
    return z
      .string()
      .refine(() => currentDepth < maxDepth, `Category hierarchy cannot exceed ${maxDepth} levels`)
  },

  // Validate that parent category exists and is not a descendant
  validParent: (categoryId?: string) => {
    return commonValidation.optionalUuid.refine(async (parentId) => {
      if (!parentId) return true
      // This would typically make an API call to validate parent
      // For now, we'll just check it's not the same as current category
      return parentId !== categoryId
    }, 'Invalid parent category selected')
  },

  // Validate category name doesn't conflict with reserved names
  notReservedName: (reservedNames: string[] = ['all', 'none', 'uncategorized']) => {
    return z.string().refine((value) => {
      const normalized = value.trim().toLowerCase()
      return !reservedNames.includes(normalized)
    }, 'Category name cannot be a reserved word')
  },
}

// Predefined category types for common electronic components
export const predefinedCategoryTypes = [
  'Resistors',
  'Capacitors',
  'Inductors',
  'Semiconductors',
  'ICs',
  'Microcontrollers',
  'Sensors',
  'Connectors',
  'Cables',
  'Switches',
  'LEDs',
  'Displays',
  'Motors',
  'Power Supplies',
  'Batteries',
  'Tools',
  'Hardware',
  'PCBs',
  'Modules',
  'Development Boards',
] as const

export const predefinedCategorySchema = z.enum(predefinedCategoryTypes)

// Type exports for TypeScript
export type BaseCategoryData = z.infer<typeof baseCategorySchema>
export type CreateCategoryData = z.infer<typeof createCategorySchema>
export type UpdateCategoryData = z.infer<typeof updateCategorySchema>
export type CategorySearchData = z.infer<typeof categorySearchSchema>
export type CategoryHierarchyData = z.infer<typeof categoryHierarchySchema>
export type BulkCategoryOperationData = z.infer<typeof bulkCategoryOperationSchema>
export type AssignCategoriesData = z.infer<typeof assignCategoriesSchema>
export type MergeCategoriesData = z.infer<typeof mergeCategoriesSchema>
export type CategoryPathData = z.infer<typeof categoryPathSchema>
export type CategoryStatsData = z.infer<typeof categoryStatsSchema>
export type PredefinedCategoryType = z.infer<typeof predefinedCategorySchema>
