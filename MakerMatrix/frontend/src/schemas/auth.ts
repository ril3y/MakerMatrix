import { z } from 'zod'
import { commonValidation, fieldConstraints } from './common'

// Login schema
export const loginSchema = z.object({
  username: commonValidation.requiredString('Username')
    .min(fieldConstraints.username.minLength, `Username must be at least ${fieldConstraints.username.minLength} characters`)
    .max(fieldConstraints.username.maxLength, `Username must be no more than ${fieldConstraints.username.maxLength} characters`),
  
  password: commonValidation.requiredString('Password')
    .min(fieldConstraints.password.minLength, `Password must be at least ${fieldConstraints.password.minLength} characters`)
    .max(fieldConstraints.password.maxLength, `Password must be no more than ${fieldConstraints.password.maxLength} characters`),
})

// User registration schema
export const registerSchema = z.object({
  username: commonValidation.requiredString('Username')
    .min(fieldConstraints.username.minLength, `Username must be at least ${fieldConstraints.username.minLength} characters`)
    .max(fieldConstraints.username.maxLength, `Username must be no more than ${fieldConstraints.username.maxLength} characters`)
    .refine(
      (val) => /^[a-zA-Z0-9_-]+$/.test(val),
      'Username can only contain letters, numbers, hyphens, and underscores'
    ),
  
  email: commonValidation.email,
  
  password: commonValidation.requiredString('Password')
    .min(fieldConstraints.password.minLength, `Password must be at least ${fieldConstraints.password.minLength} characters`)
    .max(fieldConstraints.password.maxLength, `Password must be no more than ${fieldConstraints.password.maxLength} characters`)
    .refine(
      (val) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(val),
      'Password must contain at least one lowercase letter, one uppercase letter, and one number'
    ),
  
  confirmPassword: commonValidation.requiredString('Confirm password'),
  
  roles: z.array(z.string()).default(['user']),
}).refine(
  (data) => data.password === data.confirmPassword,
  {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  }
)

// Password change schema
export const changePasswordSchema = z.object({
  currentPassword: commonValidation.requiredString('Current password'),
  
  newPassword: commonValidation.requiredString('New password')
    .min(fieldConstraints.password.minLength, `Password must be at least ${fieldConstraints.password.minLength} characters`)
    .max(fieldConstraints.password.maxLength, `Password must be no more than ${fieldConstraints.password.maxLength} characters`)
    .refine(
      (val) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(val),
      'Password must contain at least one lowercase letter, one uppercase letter, and one number'
    ),
  
  confirmNewPassword: commonValidation.requiredString('Confirm new password'),
}).refine(
  (data) => data.newPassword === data.confirmNewPassword,
  {
    message: 'New passwords do not match',
    path: ['confirmNewPassword'],
  }
).refine(
  (data) => data.currentPassword !== data.newPassword,
  {
    message: 'New password must be different from current password',
    path: ['newPassword'],
  }
)

// Password reset request schema
export const passwordResetRequestSchema = z.object({
  email: commonValidation.email,
})

// Password reset schema
export const passwordResetSchema = z.object({
  token: commonValidation.requiredString('Reset token'),
  
  newPassword: commonValidation.requiredString('New password')
    .min(fieldConstraints.password.minLength, `Password must be at least ${fieldConstraints.password.minLength} characters`)
    .max(fieldConstraints.password.maxLength, `Password must be no more than ${fieldConstraints.password.maxLength} characters`)
    .refine(
      (val) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(val),
      'Password must contain at least one lowercase letter, one uppercase letter, and one number'
    ),
  
  confirmNewPassword: commonValidation.requiredString('Confirm new password'),
}).refine(
  (data) => data.newPassword === data.confirmNewPassword,
  {
    message: 'Passwords do not match',
    path: ['confirmNewPassword'],
  }
)

// User profile update schema
export const updateProfileSchema = z.object({
  username: commonValidation.requiredString('Username')
    .min(fieldConstraints.username.minLength, `Username must be at least ${fieldConstraints.username.minLength} characters`)
    .max(fieldConstraints.username.maxLength, `Username must be no more than ${fieldConstraints.username.maxLength} characters`)
    .refine(
      (val) => /^[a-zA-Z0-9_-]+$/.test(val),
      'Username can only contain letters, numbers, hyphens, and underscores'
    ),
  
  email: commonValidation.email,
  
  is_active: z.boolean().default(true),
  
  roles: z.array(z.string()).default(['user']),
})

// User management schema (admin only)
export const userManagementSchema = z.object({
  username: commonValidation.requiredString('Username')
    .min(fieldConstraints.username.minLength, `Username must be at least ${fieldConstraints.username.minLength} characters`)
    .max(fieldConstraints.username.maxLength, `Username must be no more than ${fieldConstraints.username.maxLength} characters`)
    .refine(
      (val) => /^[a-zA-Z0-9_-]+$/.test(val),
      'Username can only contain letters, numbers, hyphens, and underscores'
    ),
  
  email: commonValidation.email,
  
  is_active: z.boolean().default(true),
  
  password_change_required: z.boolean().default(false),
  
  roles: z.array(z.string()).min(1, 'User must have at least one role'),
})

// Role schema
export const roleSchema = z.object({
  name: commonValidation.requiredString('Role name')
    .min(2, 'Role name must be at least 2 characters')
    .max(50, 'Role name must be no more than 50 characters')
    .refine(
      (val) => /^[a-zA-Z0-9_-]+$/.test(val),
      'Role name can only contain letters, numbers, hyphens, and underscores'
    ),
  
  description: commonValidation.optionalTrimmedString
    .refine(
      (val) => !val || val.length <= fieldConstraints.description.maxLength,
      `Description must be no more than ${fieldConstraints.description.maxLength} characters`
    ),
  
  permissions: z.array(z.string()).default([]),
})

// Available permissions enum
export const availablePermissions = [
  'parts:read',
  'parts:write',
  'parts:delete',
  'categories:read',
  'categories:write',
  'categories:delete',
  'locations:read',
  'locations:write',
  'locations:delete',
  'users:read',
  'users:write',
  'users:delete',
  'tasks:read',
  'tasks:write',
  'tasks:delete',
  'csv:import',
  'admin',
] as const

export const permissionSchema = z.enum(availablePermissions)

// Two-factor authentication setup schema
export const twoFactorSetupSchema = z.object({
  secret: commonValidation.requiredString('Secret key'),
  code: commonValidation.requiredString('Verification code')
    .length(6, 'Verification code must be 6 digits')
    .refine(
      (val) => /^\d{6}$/.test(val),
      'Verification code must be 6 digits'
    ),
})

// Two-factor authentication verification schema
export const twoFactorVerifySchema = z.object({
  code: commonValidation.requiredString('Verification code')
    .length(6, 'Verification code must be 6 digits')
    .refine(
      (val) => /^\d{6}$/.test(val),
      'Verification code must be 6 digits'
    ),
})

// Session management schema
export const sessionSchema = z.object({
  token: commonValidation.requiredString('Session token'),
  refresh_token: commonValidation.optionalString,
  expires_at: z.string().datetime(),
  user_id: commonValidation.uuid,
})

// API key schema (for programmatic access)
export const apiKeySchema = z.object({
  name: commonValidation.requiredString('API key name')
    .min(1, 'API key name is required')
    .max(100, 'API key name must be no more than 100 characters'),
  
  description: commonValidation.optionalTrimmedString
    .refine(
      (val) => !val || val.length <= fieldConstraints.description.maxLength,
      `Description must be no more than ${fieldConstraints.description.maxLength} characters`
    ),
  
  permissions: z.array(permissionSchema).min(1, 'API key must have at least one permission'),
  
  expires_at: z.string().datetime().optional(),
})

// Password strength validation helper
export const passwordStrengthRules = {
  minLength: fieldConstraints.password.minLength,
  maxLength: fieldConstraints.password.maxLength,
  requireLowercase: true,
  requireUppercase: true,
  requireNumbers: true,
  requireSpecialChars: false,
  commonPasswords: [
    'password',
    '123456',
    'password123',
    'admin',
    'qwerty',
    'letmein',
  ],
}

export const validatePasswordStrength = (password: string): {
  isValid: boolean
  score: number
  feedback: string[]
} => {
  const feedback: string[] = []
  let score = 0

  if (password.length < passwordStrengthRules.minLength) {
    feedback.push(`Password must be at least ${passwordStrengthRules.minLength} characters`)
  } else {
    score += 1
  }

  if (passwordStrengthRules.requireLowercase && !/[a-z]/.test(password)) {
    feedback.push('Password must contain at least one lowercase letter')
  } else {
    score += 1
  }

  if (passwordStrengthRules.requireUppercase && !/[A-Z]/.test(password)) {
    feedback.push('Password must contain at least one uppercase letter')
  } else {
    score += 1
  }

  if (passwordStrengthRules.requireNumbers && !/\d/.test(password)) {
    feedback.push('Password must contain at least one number')
  } else {
    score += 1
  }

  if (passwordStrengthRules.requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    feedback.push('Password must contain at least one special character')
  } else if (passwordStrengthRules.requireSpecialChars) {
    score += 1
  }

  if (passwordStrengthRules.commonPasswords.includes(password.toLowerCase())) {
    feedback.push('Password is too common')
    score = Math.max(0, score - 2)
  }

  return {
    isValid: feedback.length === 0,
    score: Math.max(0, Math.min(5, score)),
    feedback,
  }
}

// Type exports for TypeScript
export type LoginData = z.infer<typeof loginSchema>
export type RegisterData = z.infer<typeof registerSchema>
export type ChangePasswordData = z.infer<typeof changePasswordSchema>
export type PasswordResetRequestData = z.infer<typeof passwordResetRequestSchema>
export type PasswordResetData = z.infer<typeof passwordResetSchema>
export type UpdateProfileData = z.infer<typeof updateProfileSchema>
export type UserManagementData = z.infer<typeof userManagementSchema>
export type RoleData = z.infer<typeof roleSchema>
export type TwoFactorSetupData = z.infer<typeof twoFactorSetupSchema>
export type TwoFactorVerifyData = z.infer<typeof twoFactorVerifySchema>
export type SessionData = z.infer<typeof sessionSchema>
export type ApiKeyData = z.infer<typeof apiKeySchema>
export type PermissionType = z.infer<typeof permissionSchema>