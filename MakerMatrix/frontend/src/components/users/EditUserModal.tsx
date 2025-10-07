import { useState, useEffect } from 'react'
import { X, User, Mail, Shield, Lock } from 'lucide-react'
import type { User as UserType, UpdateUserRolesRequest } from '@/types/users'
import toast from 'react-hot-toast'

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
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) {
      setSelectedRoleIds(user.roles.map((r) => r.id))
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

          {/* Note about password */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <div className="flex gap-2">
              <Lock className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-blue-800 dark:text-blue-200 font-medium">
                  Password Changes
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                  To change password, use the "Reset Password" option in user settings.
                </p>
              </div>
            </div>
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
