import { useState, useEffect, useCallback } from 'react'
import { X, Plus, Edit3, Trash2, Search, TrendingUp, Clock, Hash } from 'lucide-react'
import { tagsService } from '@/services/tags.service'
import type { Tag, CreateTagRequest, UpdateTagRequest, TagStats } from '@/types/tags'
import TagBadge from './TagBadge'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

interface TagManagementModalProps {
  isOpen: boolean
  onClose: () => void
  onTagsChanged?: () => void
}

const TagManagementModal = ({ isOpen, onClose, onTagsChanged }: TagManagementModalProps) => {
  const [tags, setTags] = useState<Tag[]>([])
  const [stats, setStats] = useState<TagStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'usage' | 'created_at'>('usage')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Edit/create state
  const [editingTag, setEditingTag] = useState<Tag | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState<CreateTagRequest>({
    name: '',
    color: '#3B82F6',
    icon: '',
    description: '',
  })

  // Color presets
  const colorPresets = [
    '#3B82F6', // Blue
    '#10B981', // Green
    '#F59E0B', // Amber
    '#EF4444', // Red
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#14B8A6', // Teal
    '#F97316', // Orange
  ]

  // Load tags and stats
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [tagsResponse, statsResponse] = await Promise.all([
        tagsService.getAllTags({
          search: searchQuery || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          page_size: 100,
        }),
        tagsService.getTagStats(),
      ])
      setTags(tagsResponse.items || [])
      setStats(statsResponse)
    } catch (error: any) {
      console.error('Error loading tags:', error)
      toast.error('Failed to load tags')
    } finally {
      setLoading(false)
    }
  }, [searchQuery, sortBy, sortOrder])

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  // Handle create tag
  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast.error('Tag name is required')
      return
    }

    try {
      await tagsService.createTag({
        ...formData,
        name: formData.name.trim(),
      })
      toast.success('Tag created successfully')
      setShowCreateForm(false)
      setFormData({ name: '', color: '#3B82F6', icon: '', description: '' })
      loadData()
      onTagsChanged?.()
    } catch (error: any) {
      toast.error(error.message || 'Failed to create tag')
    }
  }

  // Handle update tag
  const handleUpdate = async () => {
    if (!editingTag || !formData.name.trim()) {
      toast.error('Tag name is required')
      return
    }

    try {
      const updateData: UpdateTagRequest = {
        name: formData.name.trim(),
        color: formData.color,
        icon: formData.icon || undefined,
        description: formData.description || undefined,
      }
      await tagsService.updateTag(editingTag.id, updateData)
      toast.success('Tag updated successfully')
      setEditingTag(null)
      setFormData({ name: '', color: '#3B82F6', icon: '', description: '' })
      loadData()
      onTagsChanged?.()
    } catch (error: any) {
      toast.error(error.message || 'Failed to update tag')
    }
  }

  // Handle delete tag
  const handleDelete = async (tag: Tag) => {
    if (tag.is_system_tag) {
      toast.error('Cannot delete system tags')
      return
    }

    const totalUsage = tag.parts_count + tag.tools_count
    if (totalUsage > 0) {
      if (
        !window.confirm(
          `This tag is used by ${totalUsage} item(s). Are you sure you want to delete it?`
        )
      ) {
        return
      }
    }

    try {
      await tagsService.deleteTag(tag.id)
      toast.success('Tag deleted successfully')
      loadData()
      onTagsChanged?.()
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete tag')
    }
  }

  // Start editing
  const startEdit = (tag: Tag) => {
    setEditingTag(tag)
    setFormData({
      name: tag.name,
      color: tag.color || '#3B82F6',
      icon: tag.icon || '',
      description: tag.description || '',
    })
    setShowCreateForm(false)
  }

  // Cancel edit/create
  const cancelForm = () => {
    setEditingTag(null)
    setShowCreateForm(false)
    setFormData({ name: '', color: '#3B82F6', icon: '', description: '' })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-background-primary rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-primary flex items-center gap-2">
              <Hash className="w-6 h-6" />
              Manage Tags
            </h2>
            {stats && (
              <p className="text-sm text-muted mt-1">
                {stats.total_tags} total tags ({stats.total_system_tags} system,{' '}
                {stats.total_user_tags} custom)
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-muted hover:text-primary transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Statistics */}
          {stats && (
            <div className="grid grid-cols-3 gap-4">
              <div className="card p-4">
                <div className="flex items-center gap-2 text-accent mb-2">
                  <TrendingUp className="w-4 h-4" />
                  <span className="text-sm font-medium">Most Used</span>
                </div>
                <div className="space-y-1">
                  {stats.most_used_tags.slice(0, 3).map(({ tag, usage_count }) => (
                    <div key={tag.id} className="flex items-center justify-between text-sm">
                      <TagBadge tag={tag} size="sm" />
                      <span className="text-muted">{usage_count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-4">
                <div className="flex items-center gap-2 text-accent mb-2">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm font-medium">Recent Tags</span>
                </div>
                <div className="space-y-1">
                  {stats.recent_tags.slice(0, 3).map((tag) => (
                    <TagBadge key={tag.id} tag={tag} size="sm" />
                  ))}
                </div>
              </div>

              <div className="card p-4">
                <div className="flex items-center gap-2 text-accent mb-2">
                  <Hash className="w-4 h-4" />
                  <span className="text-sm font-medium">Usage</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Parts:</span>
                    <span className="text-primary font-medium">
                      {stats.tags_by_entity_type.parts}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Tools:</span>
                    <span className="text-primary font-medium">
                      {stats.tags_by_entity_type.tools}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Create/Edit Form */}
          <AnimatePresence>
            {(showCreateForm || editingTag) && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="card p-4 space-y-4"
              >
                <h3 className="text-lg font-semibold text-primary">
                  {editingTag ? 'Edit Tag' : 'Create New Tag'}
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary mb-1">
                      Tag Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., todo, testing"
                      className="input w-full"
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary mb-1">
                      Icon (emoji)
                    </label>
                    <input
                      type="text"
                      value={formData.icon}
                      onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                      placeholder="e.g., 🔧 ⚡ 🎯"
                      className="input w-full"
                      maxLength={2}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-secondary mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Optional description..."
                    className="input w-full h-20 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-secondary mb-2">Color</label>
                  <div className="flex gap-2 flex-wrap">
                    {colorPresets.map((color) => (
                      <button
                        key={color}
                        type="button"
                        onClick={() => setFormData({ ...formData, color })}
                        className={`w-8 h-8 rounded-full transition-all ${
                          formData.color === color
                            ? 'ring-2 ring-primary ring-offset-2 ring-offset-background-primary'
                            : 'hover:scale-110'
                        }`}
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                    <input
                      type="color"
                      value={formData.color}
                      onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                      className="w-8 h-8 rounded-full cursor-pointer"
                      title="Custom color"
                    />
                  </div>
                </div>

                {/* Preview */}
                <div>
                  <label className="block text-sm font-medium text-secondary mb-2">Preview</label>
                  <TagBadge
                    tag={{
                      id: 'preview',
                      name: formData.name || 'example',
                      color: formData.color,
                      icon: formData.icon,
                      description: formData.description,
                      is_system_tag: false,
                      created_by: '',
                      created_at: '',
                      updated_at: '',
                      parts_count: 0,
                      tools_count: 0,
                    }}
                    size="md"
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={editingTag ? handleUpdate : handleCreate}
                    className="btn btn-primary"
                    disabled={!formData.name.trim()}
                  >
                    {editingTag ? 'Update Tag' : 'Create Tag'}
                  </button>
                  <button onClick={cancelForm} className="btn btn-secondary">
                    Cancel
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Search and Sort */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tags..."
                className="input pl-10 w-full"
              />
            </div>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="input w-40"
            >
              <option value="usage">Most Used</option>
              <option value="name">Name</option>
              <option value="created_at">Date Created</option>
            </select>

            {!showCreateForm && !editingTag && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="btn btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                New Tag
              </button>
            )}
          </div>

          {/* Tags List */}
          <div className="space-y-2">
            {loading ? (
              <div className="text-center py-8">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
              </div>
            ) : tags.length === 0 ? (
              <div className="text-center py-8">
                <Hash className="w-12 h-12 text-muted mx-auto mb-2" />
                <p className="text-muted">No tags found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {tags.map((tag) => (
                  <div
                    key={tag.id}
                    className="card p-4 flex items-center justify-between hover:bg-background-secondary transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <TagBadge tag={tag} size="md" showCount />
                      {tag.description && (
                        <p className="text-sm text-muted truncate">{tag.description}</p>
                      )}
                      {tag.is_system_tag && (
                        <span className="px-2 py-1 bg-accent/10 text-accent text-xs rounded">
                          System
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="text-sm text-muted">
                        {tag.parts_count} parts · {tag.tools_count} tools
                      </div>
                      {!tag.is_system_tag && (
                        <>
                          <button
                            onClick={() => startEdit(tag)}
                            className="btn btn-secondary btn-sm"
                            title="Edit tag"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(tag)}
                            className="btn btn-secondary btn-sm text-red-500 hover:text-red-600"
                            title="Delete tag"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border flex justify-end">
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default TagManagementModal
