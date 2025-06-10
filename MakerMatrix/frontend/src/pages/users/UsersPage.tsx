import { motion } from 'framer-motion'
import { Users, Plus, Search, Filter, UserCheck, UserX, Shield, Edit, Trash2, MoreVertical } from 'lucide-react'
import { useState, useEffect } from 'react'
import { usersService } from '@/services/users.service'
import { User, UserStats, Role } from '@/types/users'
import toast from 'react-hot-toast'

const UsersPage = () => {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [stats, setStats] = useState<UserStats>({ total: 0, active: 0, inactive: 0, admins: 0 })
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [usersData, rolesData, statsData] = await Promise.all([
        usersService.getAllUsers(),
        usersService.getAllRoles(),
        usersService.getUserStats()
      ])
      setUsers(usersData)
      setRoles(rolesData)
      setStats(statsData)
    } catch (error) {
      toast.error('Failed to load users data')
      console.error('Error loading users:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return
    
    try {
      await usersService.deleteUser(userId)
      toast.success('User deleted successfully')
      loadData()
    } catch (error) {
      toast.error('Failed to delete user')
    }
  }

  const handleToggleUserStatus = async (userId: string, isActive: boolean) => {
    try {
      await usersService.toggleUserStatus(userId, !isActive)
      toast.success(`User ${isActive ? 'deactivated' : 'activated'} successfully`)
      loadData()
    } catch (error) {
      toast.error('Failed to update user status')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Users className="w-6 h-6" />
            Users
          </h1>
          <p className="text-text-secondary mt-1">
            Manage user accounts and permissions
          </p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </motion.div>

      {/* Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-4"
      >
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search users..."
              className="input pl-10 w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </motion.div>

      {/* User Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Users className="w-8 h-8 text-primary" />
            <div>
              <p className="text-sm text-text-secondary">Total Users</p>
              <p className="text-2xl font-bold text-text-primary">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <UserCheck className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-text-secondary">Active Users</p>
              <p className="text-2xl font-bold text-text-primary">{stats.active}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <UserX className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-text-secondary">Inactive Users</p>
              <p className="text-2xl font-bold text-text-primary">{stats.inactive}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-accent" />
            <div>
              <p className="text-sm text-text-secondary">Admins</p>
              <p className="text-2xl font-bold text-text-primary">{stats.admins}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Users List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.175 }}
        className="card overflow-hidden"
      >
        <div className="p-4 border-b border-border">
          <h3 className="text-lg font-semibold text-text-primary">Users</h3>
        </div>
        
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="text-text-secondary mt-2">Loading users...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="w-12 h-12 text-text-muted mx-auto mb-2" />
            <p className="text-text-secondary">No users found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="text-left py-3 px-4 font-medium text-text-secondary">User</th>
                  <th className="text-left py-3 px-4 font-medium text-text-secondary">Email</th>
                  <th className="text-left py-3 px-4 font-medium text-text-secondary">Roles</th>
                  <th className="text-left py-3 px-4 font-medium text-text-secondary">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-text-secondary">Created</th>
                  <th className="text-center py-3 px-4 font-medium text-text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="border-b border-border hover:bg-background-secondary/50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span className="font-medium text-text-primary">{user.username}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-text-secondary">{user.email}</td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((role) => (
                          <span 
                            key={role.id}
                            className="inline-block px-2 py-1 text-xs rounded-full bg-primary/20 text-primary"
                          >
                            {role.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-1 text-xs rounded-full ${
                        user.is_active 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-text-secondary">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleToggleUserStatus(user.id, user.is_active)}
                          className="p-1 rounded hover:bg-background-secondary"
                          title={user.is_active ? 'Deactivate user' : 'Activate user'}
                        >
                          {user.is_active ? (
                            <UserX className="w-4 h-4 text-red-500" />
                          ) : (
                            <UserCheck className="w-4 h-4 text-green-500" />
                          )}
                        </button>
                        <button
                          onClick={() => setSelectedUser(user)}
                          className="p-1 rounded hover:bg-background-secondary"
                          title="Edit user"
                        >
                          <Edit className="w-4 h-4 text-text-secondary" />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.id)}
                          className="p-1 rounded hover:bg-background-secondary"
                          title="Delete user"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default UsersPage