import { useState, useEffect } from 'react'
import { X, User, Mail, Shield, Lock, Eye, EyeOff, Key } from 'lucide-react'
import type { User as UserType, UpdateUserRolesRequest } from '@/types/users'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'

interface EditUserModalProps {
  isOpen: boolean
  onClose: () => void
  user: UserType | null
  onUpdateRoles: (userId: string, roleData: UpdateUserRolesRequest) => Promise<void>
  availableRoles: Array<{ id: string; name: string }>
}

const EditUserModal = ({
  isOpen,
  onClose,
  user,
  onUpdateRoles,
  availableRoles,
}: EditUserModalProps) => {
  const { user: currentUser, hasRole } = useAuth(false)
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [showPasswordSection, setShowPasswordSection] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Check if current user is admin
  const isAdmin = hasRole('admin')
  // Check if editing own profile
  const isEditingSelf = currentUser?.id === user?.id

  // Determine if current password is required
  // Admin editing another user = NO current password needed
  // Anyone editing themselves = YES current password needed
  const requireCurrentPassword = !isAdmin || isEditingSelf

  // Debug logging
  useEffect(() => {
    if (isOpen && user) {
      console.log('=== EditUserModal Debug ===')
      console.log('Current User ID:', currentUser?.id)
      console.log('Editing User ID:', user?.id)
      console.log('Current User Roles:', currentUser?.roles?.map(r => r.name))
      console.log('isAdmin:', isAdmin)
      console.log('isEditingSelf:', isEditingSelf)
      console.log('requireCurrentPassword:', requireCurrentPassword)
      console.log('=========================')
    }
  }, [isOpen, user, currentUser, isAdmin, isEditingSelf, requireCurrentPassword])

  useEffect(() => {
    if (user) {
      setSelectedRoleIds(user.roles.map((r) => r.id))
      // Reset password fields when modal opens
      setShowPasswordSection(false)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!user) return

    if (selectedRoleIds.length === 0) {
      toast.error('Please select at least one role')
      return
    }

    try {
      setLoading(true)
      const response = await onUpdateRoles(user.id, { role_ids: selectedRoleIds })

      // Check if response contains warning about revoked API keys
      const message = response?.message || 'User roles updated successfully'

      if (message.includes('⚠️') || message.includes('API key')) {
        // Show warning toast for API key revocation
        toast(message, {
          icon: '⚠️',
          duration: 8000, // Show longer for important security message
          style: {
            background: '#FEF3C7',
            color: '#92400E',
            border: '1px solid #FCD34D',
          },
        })
      } else {
        toast.success(message)
      }

      onClose()
    } catch (error) {
      const err = error as { response?: { data?: { message?: string } } }
      toast.error(err?.response?.data?.message || 'Failed to update user roles')
    } finally {
      setLoading(false)
    }
  }

  const toggleRole = (roleId: string) => {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
    )
  }

  const handlePasswordChange = async () => {
    if (!user) return

    // Validation - use the requireCurrentPassword from component state
    if (requireCurrentPassword && !currentPassword) {
      toast.error('Please enter your current password')
      return
    }

    if (!newPassword || !confirmPassword) {
      toast.error('Please fill in all password fields')
      return
    }

    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters')
      return
    }

    if (!/[A-Z]/.test(newPassword)) {
      toast.error('Password must contain at least one uppercase letter')
      return
    }

    if (!/[a-z]/.test(newPassword)) {
      toast.error('Password must contain at least one lowercase letter')
      return
    }

    if (!/[0-9]/.test(newPassword)) {
      toast.error('Password must contain at least one number')
      return
    }

    if (requireCurrentPassword && newPassword === currentPassword) {
      toast.error('New password must be different from current password')
      return
    }

    try {
      setLoading(true)
      const payload: any = {
        new_password: newPassword,
      }

      // Only include current_password if required
      if (requireCurrentPassword) {
        payload.current_password = currentPassword
      }

      const response = await apiClient.put(`/api/users/${user.id}/password`, payload)

      if (response.status === 'success') {
        toast.success('Password changed successfully!')
        setShowPasswordSection(false)
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
      } else {
        toast.error(response.message || 'Failed to change password')
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !user) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background-primary rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-primary flex items-center gap-2">
            <User className="w-5 h-5" />
            Edit User
          </h2>
          <button onClick={onClose} className="text-secondary hover:text-primary transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* User Info (Read-only) */}
          <div className="bg-background-secondary rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-muted" />
              <div>
                <p className="text-xs text-secondary">Username</p>
                <p className="text-sm font-medium text-primary">{user.username}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-muted" />
              <div>
                <p className="text-xs text-secondary">Email</p>
                <p className="text-sm font-medium text-primary">{user.email}</p>
              </div>
            </div>
          </div>

          {/* Roles */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Roles *
            </label>
            <div className="space-y-2 border border-border rounded-lg p-3">
              {availableRoles.length === 0 ? (
                <p className="text-sm text-secondary">No roles available</p>
              ) : (
                availableRoles.map((role) => (
                  <label
                    key={role.id}
                    className="flex items-center gap-2 cursor-pointer hover:bg-background-secondary p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRoleIds.includes(role.id)}
                      onChange={() => toggleRole(role.id)}
                      className="rounded border-border"
                    />
                    <span className="text-sm text-primary">{role.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Password Change Section */}
          <div className="border border-border rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setShowPasswordSection(!showPasswordSection)}
              className="w-full flex items-center justify-between p-3 bg-background-secondary hover:bg-background-tertiary transition-colors"
            >
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-muted" />
                <span className="text-sm font-medium text-primary">Change Password</span>
              </div>
              <Lock className={`w-4 h-4 text-muted transition-transform ${showPasswordSection ? 'rotate-90' : ''}`} />
            </button>

            {showPasswordSection && (
              <div className="p-4 space-y-3 border-t border-border">
                {/* Admin Notice - show when admin is editing another user */}
                {!requireCurrentPassword && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 mb-3">
                    <p className="text-xs text-blue-800 dark:text-blue-200">
                      ℹ️ As an admin, you can change this user's password without their current password.
                    </p>
                  </div>
                )}

                {/* Current Password - only show if required */}
                {requireCurrentPassword && (
                  <div>
                    <label className="block text-xs font-medium text-secondary mb-1">
                      Current Password *
                    </label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? 'text' : 'password'}
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="input w-full pr-10"
                        placeholder="Enter current password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
                      >
                        {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}

                {/* New Password */}
                <div>
                  <label className="block text-xs font-medium text-secondary mb-1">
                    New Password *
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="input w-full pr-10"
                      placeholder="Enter new password (min 8 chars)"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
                    >
                      {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-xs font-medium text-secondary mb-1">
                    Confirm New Password *
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="input w-full pr-10"
                      placeholder="Confirm new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-primary"
                    >
                      {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Password Requirements */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2">
                  <p className="text-xs text-blue-800 dark:text-blue-200">
                    Must be at least 8 characters with uppercase, lowercase, and number
                  </p>
                </div>

                {/* Change Password Button */}
                <button
                  type="button"
                  onClick={handlePasswordChange}
                  disabled={loading}
                  className="btn btn-primary w-full"
                >
                  {loading ? 'Changing Password...' : 'Change Password'}
                </button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary flex-1"
              disabled={loading}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary flex-1" disabled={loading}>
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EditUserModal
