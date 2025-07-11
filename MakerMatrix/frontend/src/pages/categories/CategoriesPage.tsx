import { motion } from 'framer-motion'
import { Tag, Plus, Search, Filter, Tags, Hash, Edit2, Trash2, Package } from 'lucide-react'
import { useState, useEffect, useMemo } from 'react'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import EditCategoryModal from '@/components/categories/EditCategoryModal'
import { categoriesService } from '@/services/categories.service'
import { Category } from '@/types/categories'
import LoadingScreen from '@/components/ui/LoadingScreen'

const CategoriesPage = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const loadCategories = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await categoriesService.getAllCategories()
      setCategories(data)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load categories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  const handleCategoryAdded = () => {
    loadCategories()
    setShowAddModal(false)
  }

  const handleCategoryUpdated = () => {
    loadCategories()
    setShowEditModal(false)
    setEditingCategory(null)
  }

  const handleEdit = (category: Category) => {
    setEditingCategory(category)
    setShowEditModal(true)
  }

  const handleDelete = async (category: Category) => {
    if (!confirm(`Are you sure you want to delete "${category.name}"? This action cannot be undone.`)) {
      return
    }

    try {
      await categoriesService.deleteCategory({ id: category.id.toString() })
      loadCategories()
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to delete category')
    }
  }

  const filteredCategories = categoriesService.filterCategories(categories, searchTerm)
  const sortedCategories = categoriesService.sortCategoriesByName(filteredCategories)

  const stats = {
    total: categories.length,
    active: categories.length, // All categories are active for now
    mostUsed: categories.length > 0 ? categories[0].name : '-'
  }

  // Get existing category names for validation (memoized to prevent unnecessary re-renders)
  const existingCategories = useMemo(() => categories.map(cat => cat.name), [categories])

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Tag className="w-6 h-6" />
            Categories
          </h1>
          <p className="text-secondary mt-1">
            Organize parts with categories and tags
          </p>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Category
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
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="text"
              placeholder="Search categories..."
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

      {/* Category Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Tags className="w-8 h-8 text-primary" />
            <div>
              <p className="text-sm text-secondary">Total Categories</p>
              <p className="text-2xl font-bold text-primary">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Hash className="w-8 h-8 text-secondary" />
            <div>
              <p className="text-sm text-secondary">Active Categories</p>
              <p className="text-2xl font-bold text-primary">{stats.active}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <Tag className="w-8 h-8 text-accent" />
            <div>
              <p className="text-sm text-secondary">Most Used</p>
              <p className="text-xl font-bold text-primary">{stats.mostUsed}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Popular Categories */}
      {categories.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.175 }}
          className="card p-4"
        >
          <h3 className="text-lg font-semibold text-primary mb-4">All Categories</h3>
          <div className="flex flex-wrap gap-2">
            {categories.slice(0, 10).map((category) => (
              <span
                key={category.id}
                className="px-3 py-1 bg-primary-10 text-primary rounded-full text-sm cursor-pointer hover:bg-primary-20 transition-colors"
                onClick={() => handleEdit(category)}
                title={category.description || 'Click to edit'}
              >
                {category.name}
              </span>
            ))}
            {categories.length > 10 && (
              <span className="px-3 py-1 text-secondary text-sm">
                +{categories.length - 10} more
              </span>
            )}
          </div>
        </motion.div>
      )}

      {/* Categories List */}
      {loading ? (
        <LoadingScreen />
      ) : error ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6 text-center"
        >
          <p className="text-red-500">{error}</p>
        </motion.div>
      ) : sortedCategories.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6 text-center"
        >
          <Tag className="w-16 h-16 text-muted mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-primary mb-2">
            {searchTerm ? 'No categories found' : 'No categories yet'}
          </h3>
          <p className="text-secondary">
            {searchTerm ? 'Try adjusting your search terms' : 'Click "Add Category" to create your first category'}
          </p>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-4 text-secondary font-medium">Name</th>
                  <th className="text-left p-4 text-secondary font-medium">Description</th>
                  <th className="text-center p-4 text-secondary font-medium">Parts Count</th>
                  <th className="text-right p-4 text-secondary font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedCategories.map((category) => (
                  <tr key={category.id} className="border-b border-border hover:bg-background-secondary transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <Tag className="w-4 h-4 text-primary" />
                        <span className="font-medium text-primary">{category.name}</span>
                      </div>
                    </td>
                    <td className="p-4 text-secondary">
                      {category.description || '-'}
                    </td>
                    <td className="p-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Package className="w-4 h-4 text-muted" />
                        <span className="text-secondary">{category.part_count || 0}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleEdit(category)}
                          className="btn btn-icon btn-secondary"
                          title="Edit category"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(category)}
                          className="btn btn-icon btn-secondary text-red-400 hover:text-red-300"
                          title="Delete category"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Add Category Modal */}
      <AddCategoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleCategoryAdded}
        existingCategories={existingCategories}
      />

      {/* Edit Category Modal */}
      {editingCategory && (
        <EditCategoryModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false)
            setEditingCategory(null)
          }}
          onSuccess={handleCategoryUpdated}
          category={editingCategory}
          existingCategories={existingCategories.filter(name => name !== editingCategory.name)}
        />
      )}
    </div>
  )
}

export default CategoriesPage