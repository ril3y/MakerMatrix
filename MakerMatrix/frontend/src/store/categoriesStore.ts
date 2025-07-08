import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { Category, CreateCategoryRequest, UpdateCategoryRequest } from '@/types/categories'
import { categoriesService } from '@/services/categories.service'
import { toast } from 'react-hot-toast'

interface CategoriesState {
  // Category data
  categories: Category[]
  currentCategory: Category | null
  
  // UI state
  isLoading: boolean
  isLoadingCategory: boolean
  error: string | null
  
  // Search and filter state
  searchQuery: string
  filteredCategories: Category[]
  
  // Actions
  loadCategories: () => Promise<void>
  loadCategory: (id: string) => Promise<void>
  createCategory: (data: CreateCategoryRequest) => Promise<Category>
  updateCategory: (data: UpdateCategoryRequest) => Promise<Category>
  deleteCategory: (id: string) => Promise<void>
  deleteAllCategories: () => Promise<void>
  
  // Search and filter
  setSearchQuery: (query: string) => void
  searchCategories: (query: string) => void
  
  // Utility methods
  getCategoryById: (id: string) => Category | undefined
  getCategoryByName: (name: string) => Category | undefined
  getCategoriesByIds: (ids: string[]) => Category[]
  sortCategoriesByName: () => void
  
  // UI helpers
  clearError: () => void
  setCurrentCategory: (category: Category | null) => void
}

export const useCategoriesStore = create<CategoriesState>()(
  devtools(
    (set, get) => ({
      // Initial state
      categories: [],
      currentCategory: null,
      isLoading: false,
      isLoadingCategory: false,
      error: null,
      searchQuery: '',
      filteredCategories: [],

      // Load all categories
      loadCategories: async () => {
        set({ isLoading: true, error: null })
        try {
          const categories = await categoriesService.getAllCategories()
          set({ 
            categories, 
            filteredCategories: categories,
            isLoading: false 
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Failed to load categories',
          })
        }
      },

      // Load single category
      loadCategory: async (id) => {
        set({ isLoadingCategory: true, error: null })
        try {
          const category = await categoriesService.getCategory({ id })
          set({ currentCategory: category, isLoadingCategory: false })
        } catch (error: any) {
          set({
            isLoadingCategory: false,
            error: error.message || 'Failed to load category',
          })
        }
      },

      // Create new category
      createCategory: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const newCategory = await categoriesService.createCategory(data)
          
          // Refresh the categories list
          await get().loadCategories()
          
          toast.success('Category created successfully')
          return newCategory
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Update category
      updateCategory: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const updatedCategory = await categoriesService.updateCategory(data)
          
          // Update the current category if it's the one being edited
          if (get().currentCategory?.id === data.id) {
            set({ currentCategory: updatedCategory })
          }
          
          // Refresh the categories list
          await get().loadCategories()
          
          toast.success('Category updated successfully')
          return updatedCategory
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Delete category
      deleteCategory: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await categoriesService.deleteCategory({ id })
          
          // Clear current category if it's the one being deleted
          if (get().currentCategory?.id === id) {
            set({ currentCategory: null })
          }
          
          // Refresh the categories list
          await get().loadCategories()
          
          toast.success('Category deleted successfully')
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Delete all categories
      deleteAllCategories: async () => {
        set({ isLoading: true, error: null })
        try {
          await categoriesService.deleteAllCategories()
          
          // Clear all categories
          set({ 
            categories: [], 
            filteredCategories: [],
            currentCategory: null 
          })
          
          toast.success('All categories deleted successfully')
        } catch (error: any) {
          set({ isLoading: false })
          throw error
        }
      },

      // Search and filter
      setSearchQuery: (query) => {
        set({ searchQuery: query })
        get().searchCategories(query)
      },

      searchCategories: (query) => {
        const categories = get().categories
        if (!query.trim()) {
          set({ filteredCategories: categories })
          return
        }
        
        const filtered = categoriesService.filterCategories(categories, query)
        set({ filteredCategories: filtered })
      },

      // Utility methods
      getCategoryById: (id) => {
        return get().categories.find(category => category.id === id)
      },

      getCategoryByName: (name) => {
        return get().categories.find(category => category.name === name)
      },

      getCategoriesByIds: (ids) => {
        return categoriesService.getCategoriesByIds(get().categories, ids)
      },

      sortCategoriesByName: () => {
        const categories = get().categories
        const sorted = categoriesService.sortCategoriesByName(categories)
        set({ 
          categories: sorted, 
          filteredCategories: get().searchQuery 
            ? categoriesService.filterCategories(sorted, get().searchQuery)
            : sorted 
        })
      },

      // UI helpers
      clearError: () => set({ error: null }),
      setCurrentCategory: (category) => set({ currentCategory: category }),
    })
  )
)