import { useState, useEffect } from 'react'
import { Key, Plus, Trash2, Copy, Eye, EyeOff, RefreshCw, Shield, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiKeyService } from '@/services/apiKey.service'

interface APIKey {
  id: string
  name: string
  description: string | null
  key_prefix: string
  permissions: string[]
  role_names: string[]
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_used_at: string | null
  usage_count: number
  allowed_ips: string[]
  is_expired: boolean
  is_valid: boolean
}

interface NewKeyData {
  name: string
  description: string
  expires_in_days: number | null
  role_names: string[]
  permissions: string[]
  allowed_ips: string[]
}

const ApiKeyManagement = () => {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newKeyData, setNewKeyData] = useState<NewKeyData>({
    name: '',
    description: '',
    expires_in_days: 365,
    role_names: [],
    permissions: [],
    allowed_ips: []
  })
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [showKey, setShowKey] = useState<string | null>(null)

  useEffect(() => {
    loadApiKeys()
  }, [])

  const loadApiKeys = async () => {
    try {
      setLoading(true)
      const keys = await apiKeyService.getUserApiKeys()
      setApiKeys(keys || [])
    } catch (error: any) {
      // Check if it's an authentication error
      if (error?.response?.status === 401) {
        toast.error('Session expired. Please log in again.')
      } else {
        toast.error('Failed to load API keys')
      }
      setApiKeys([]) // Ensure apiKeys is always an array
    } finally {
      setLoading(false)
    }
  }

  const createApiKey = async () => {
    try {
      const result = await apiKeyService.createApiKey(newKeyData)
      setCreatedKey(result.api_key)
      setShowCreateForm(false)
      setNewKeyData({
        name: '',
        description: '',
        expires_in_days: 365,
        role_names: [],
        permissions: [],
        allowed_ips: []
      })
      await loadApiKeys()
      toast.success('API key created successfully')
    } catch (error) {
      toast.error('Failed to create API key')
    }
  }

  const revokeApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return

    try {
      await apiKeyService.revokeApiKey(keyId)
      await loadApiKeys()
      toast.success('API key revoked successfully')
    } catch (error) {
      toast.error('Failed to revoke API key')
    }
  }

  const deleteApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to permanently delete this API key? This action cannot be undone!')) return

    try {
      await apiKeyService.deleteApiKey(keyId)
      await loadApiKeys()
      toast.success('API key deleted successfully')
    } catch (error) {
      toast.error('Failed to delete API key')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Key className="w-5 h-5" />
            API Keys
          </h3>
          <p className="text-sm text-secondary mt-1">
            Manage API keys for programmatic access to MakerMatrix
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Created Key Display */}
      {createdKey && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-medium text-green-800 dark:text-green-200">API Key Created Successfully</h4>
              <p className="text-sm text-green-600 dark:text-green-300 mt-1">
                Make sure to copy your API key now. You won't be able to see it again!
              </p>
              <div className="mt-3 flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-green-200 dark:border-green-700 rounded text-sm font-mono">
                  {showKey === 'created' ? createdKey : '••••••••••••••••••••••••••••••••'}
                </code>
                <button
                  onClick={() => setShowKey(showKey === 'created' ? null : 'created')}
                  className="btn btn-secondary btn-sm"
                >
                  {showKey === 'created' ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => copyToClipboard(createdKey)}
                  className="btn btn-primary btn-sm flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy
                </button>
              </div>
              <button
                onClick={() => setCreatedKey(null)}
                className="mt-3 text-sm text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300"
              >
                I've saved my key
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <div className="card p-6 space-y-4">
          <h4 className="font-medium text-primary">Create New API Key</h4>

          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              Name *
            </label>
            <input
              type="text"
              className="input w-full"
              value={newKeyData.name}
              onChange={(e) => setNewKeyData({ ...newKeyData, name: e.target.value })}
              placeholder="e.g., Production API Key"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              Description
            </label>
            <textarea
              className="input w-full"
              value={newKeyData.description}
              onChange={(e) => setNewKeyData({ ...newKeyData, description: e.target.value })}
              placeholder="Optional description of this API key's purpose"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              Expires In (Days)
            </label>
            <input
              type="number"
              className="input w-full"
              value={newKeyData.expires_in_days || ''}
              onChange={(e) => setNewKeyData({ ...newKeyData, expires_in_days: e.target.value ? parseInt(e.target.value) : null })}
              placeholder="365 (leave empty for no expiration)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              Allowed IPs (Optional)
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="Comma-separated IPs (e.g., 192.168.1.100, 10.0.0.50)"
              onChange={(e) => {
                const ips = e.target.value.split(',').map(ip => ip.trim()).filter(Boolean)
                setNewKeyData({ ...newKeyData, allowed_ips: ips })
              }}
            />
            <p className="text-xs text-secondary mt-1">
              Leave empty to allow access from any IP address
            </p>
          </div>

          <div className="flex gap-2 pt-4">
            <button
              onClick={createApiKey}
              disabled={!newKeyData.name}
              className="btn btn-primary"
            >
              Create Key
            </button>
            <button
              onClick={() => setShowCreateForm(false)}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* API Keys List */}
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading API keys...</p>
        </div>
      ) : apiKeys.length > 0 ? (
        <div className="space-y-4">
          {apiKeys.map((key) => (
            <div
              key={key.id}
              className={`border rounded-lg p-4 ${
                key.is_valid
                  ? 'border-border bg-background-secondary'
                  : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-primary">{key.name}</h4>
                    <span className={`inline-block px-2 py-1 rounded text-xs ${
                      key.is_valid
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : key.is_expired
                        ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {key.is_valid ? 'Active' : key.is_expired ? 'Expired' : 'Revoked'}
                    </span>
                  </div>
                  {key.description && (
                    <p className="text-sm text-secondary mt-1">{key.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-secondary">
                    <span className="flex items-center gap-1">
                      <Key className="w-3 h-3" />
                      {key.key_prefix}...
                    </span>
                    <span>Created: {formatDate(key.created_at)}</span>
                    <span>Last used: {formatDate(key.last_used_at)}</span>
                    <span>Uses: {key.usage_count}</span>
                    {key.expires_at && (
                      <span>Expires: {formatDate(key.expires_at)}</span>
                    )}
                  </div>
                  {key.allowed_ips.length > 0 && (
                    <div className="mt-2 text-sm">
                      <span className="text-secondary">Allowed IPs: </span>
                      <span className="text-primary font-mono">{key.allowed_ips.join(', ')}</span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  {key.is_active && !key.is_expired && (
                    <button
                      onClick={() => revokeApiKey(key.id)}
                      className="btn btn-secondary btn-sm flex items-center gap-1"
                      title="Revoke this key"
                    >
                      <Shield className="w-4 h-4" />
                      Revoke
                    </button>
                  )}
                  <button
                    onClick={() => deleteApiKey(key.id)}
                    className="btn btn-danger btn-sm flex items-center gap-1"
                    title="Permanently delete this key"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 border border-dashed border-border rounded-lg">
          <Key className="w-12 h-12 text-muted mx-auto mb-2" />
          <h3 className="text-lg font-semibold text-primary mb-2">
            No API Keys
          </h3>
          <p className="text-secondary mb-4">
            Create an API key to access MakerMatrix programmatically
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn btn-primary"
          >
            Create Your First API Key
          </button>
        </div>
      )}

      {/* Usage Information */}
      <div className="border-t border-border pt-6">
        <h4 className="font-medium text-primary mb-3">Using API Keys</h4>
        <div className="space-y-2 text-sm text-secondary">
          <p>Include your API key in requests using one of these headers:</p>
          <div className="bg-background-tertiary rounded p-3 space-y-2 font-mono text-xs">
            <div><span className="text-primary">X-API-Key:</span> your_api_key_here</div>
            <div><span className="text-primary">Authorization:</span> ApiKey your_api_key_here</div>
          </div>
          <p className="pt-2">
            API keys inherit permissions from your user roles. Keep your keys secure and never commit them to version control.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ApiKeyManagement
