import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  ArrowLeft,
  Save,
  Trash2,
  Package,
  Plus,
  X,
  Info,
  AlertCircle,
  CheckCircle,
  HelpCircle,
} from 'lucide-react'
import { TooltipIcon } from '../../components/ui/Tooltip'
import type { SupplierEnrichmentRequirements } from '../../services/parts.service'
import { partsService } from '../../services/parts.service'
import { locationsService } from '../../services/locations.service'
import { categoriesService } from '../../services/categories.service'
import { projectsService } from '../../services/projects.service'
import { supplierService } from '../../services/supplier.service'
import type { Part, CreatePartRequest } from '../../types/parts'
import type { Location } from '../../types/locations'
import type { Category } from '../../types/categories'
import type { Project } from '../../types/projects'
import FormField from '../../components/ui/FormField'
import ImageUpload from '../../components/ui/ImageUpload'
import EmojiPicker from '../../components/ui/EmojiPicker'
import AddCategoryModal from '../../components/categories/AddCategoryModal'
import AddLocationModal from '../../components/locations/AddLocationModal'
import ContainerSlotPickerModal from '../../components/locations/ContainerSlotPickerModal'
import CategorySelector from '../../components/ui/CategorySelector'
import AddProjectModal from '../../components/projects/AddProjectModal'
import { HierarchicalLocationPicker } from '../../components/locations/HierarchicalLocationPicker'
import SupplierSelector from '../../components/ui/SupplierSelector'
import { CustomSelect } from '../../components/ui/CustomSelect'
import toast from 'react-hot-toast'

const partSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  part_number: z.string().optional(),
  supplier_part_number: z.string().optional(),
  description: z.string().optional(),
  quantity: z.number().min(0, 'Quantity must be non-negative'),
  minimum_quantity: z.number().min(0, 'Minimum quantity must be non-negative').optional(),
  location_id: z.string().optional(),
  supplier: z.string().optional(),
  supplier_url: z.string().optional(),
  product_url: z.string().optional(),
  image_url: z.string().optional(),
  emoji: z.string().optional(),
  manufacturer: z.string().optional(), // Enriched field
  manufacturer_part_number: z.string().optional(), // Enriched field
  component_type: z.string().optional(), // Enriched field
  category_ids: z.array(z.string()).optional(),
})

type PartFormData = z.infer<typeof partSchema>

const EditPartPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [part, setPart] = useState<Part | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])
  const [additionalProperties, setAdditionalProperties] = useState<Record<string, any>>({})
  const [newPropertyKey, setNewPropertyKey] = useState('')
  const [newPropertyValue, setNewPropertyValue] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false)
  const [showAddProjectModal, setShowAddProjectModal] = useState(false)
  const [showAddLocationModal, setShowAddLocationModal] = useState(false)
  const [showSlotPickerModal, setShowSlotPickerModal] = useState(false)
  const [selectedContainer, setSelectedContainer] = useState<Location | null>(null)
  const [enrichmentRequirements, setEnrichmentRequirements] =
    useState<SupplierEnrichmentRequirements | null>(null)
  const [loadingRequirements, setLoadingRequirements] = useState(false)

  const buildLocationHierarchy = (
    locations: Location[]
  ): Array<{ id: string; name: string; level: number }> => {
    const result: Array<{ id: string; name: string; level: number }> = []

    const addLocation = (location: Location, level: number = 0) => {
      result.push({
        id: location.id,
        name: location.name,
        level,
      })

      // Find children in the flat list
      const children = locations.filter((loc) => loc.parent_id === location.id)
      children
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach((child) => addLocation(child, level + 1))
    }

    // Start with root locations (no parent_id)
    const rootLocations = locations.filter((loc) => !loc.parent_id)
    rootLocations
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((location) => addLocation(location))

    return result
  }

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
    setValue,
    watch,
    reset,
  } = useForm<PartFormData>({
    resolver: zodResolver(partSchema),
    mode: 'onChange', // Enable validation on change
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        if (!id) return

        const [partData, locationsData, categoriesData, projectsData] = await Promise.all([
          partsService.getPart(id),
          locationsService.getAllLocations({ hide_auto_slots: false }), // Get all locations including slots
          categoriesService.getAll(),
          projectsService.getAllProjects(),
        ])

        setPart(partData)
        setLocations(locationsData)
        setCategories(categoriesData)
        setProjects(projectsData)

        // Set additional properties
        setAdditionalProperties(partData.additional_properties || {})

        // Set selected categories
        const categoryIds = partData.categories?.map((cat) => cat.id) || []
        setSelectedCategories(categoryIds)

        // Set selected projects
        const projectIds = partData.projects?.map((proj) => proj.id) || []
        console.log('Initial projects loaded:', {
          partDataProjects: partData.projects,
          projectIds,
        })
        setSelectedProjects(projectIds)

        // Populate form with existing data using reset() for proper form population
        reset({
          name: partData.name,
          part_number: partData.part_number || '',
          supplier_part_number: partData.supplier_part_number || '',
          description: partData.description || '',
          quantity: partData.quantity,
          minimum_quantity: partData.minimum_quantity || 0,
          location_id: partData.location_id || undefined,
          supplier: partData.supplier || '',
          supplier_url: partData.supplier_url || '',
          product_url: partData.product_url || '',
          image_url: partData.image_url || '',
          emoji: partData.emoji || '',
          manufacturer: partData.manufacturer || '', // CRITICAL: Preserve enriched data
          manufacturer_part_number: partData.manufacturer_part_number || '', // CRITICAL: Preserve enriched data
          component_type: partData.component_type || '', // CRITICAL: Preserve enriched data
          category_ids: categoryIds,
        })
      } catch (error) {
        console.error('Error loading part data:', error)
        toast.error('Failed to load part data')
        navigate('/parts')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [id, reset, navigate])

  // Watch supplier field
  const supplierValue = watch('supplier')

  // Debug: Watch selectedProjects changes
  useEffect(() => {
    console.log('selectedProjects state changed:', selectedProjects)
  }, [selectedProjects])

  const loadEnrichmentRequirements = useCallback(async (supplier: string) => {
    try {
      setLoadingRequirements(true)

      // Known API suppliers with enrichment capabilities
      const knownApiSuppliers = ['lcsc', 'digikey', 'mouser', 'octopart', 'arrow', 'newark']

      // Check if this is a known API supplier before making the request
      const isKnownApiSupplier = knownApiSuppliers.includes(supplier.toLowerCase())

      if (!isKnownApiSupplier) {
        // Simple supplier without API capabilities - skip the API call
        console.log(
          `Supplier "${supplier}" is not a known API supplier - skipping enrichment check`
        )
        setEnrichmentRequirements(null)
        return
      }

      // Get supplier capabilities (only for known API suppliers)
      const capabilities = await supplierService.getSupplierCapabilities(supplier)

      // Only load enrichment requirements if supplier has enrichment capabilities
      const hasEnrichmentCapabilities = capabilities.some(
        (cap) =>
          cap === 'get_part_details' ||
          cap === 'fetch_datasheet' ||
          cap === 'fetch_image' ||
          cap === 'fetch_pricing_stock'
      )

      if (hasEnrichmentCapabilities) {
        const requirements = await partsService.getSupplierEnrichmentRequirements(supplier)
        setEnrichmentRequirements(requirements)
      } else {
        // API supplier without enrichment capabilities
        setEnrichmentRequirements(null)
      }
    } catch (error) {
      console.error('Failed to load enrichment requirements:', error)
      // Don't show error toast - this is optional information
      setEnrichmentRequirements(null)
    } finally {
      setLoadingRequirements(false)
    }
  }, [])

  // Load enrichment requirements when supplier changes
  useEffect(() => {
    if (supplierValue && supplierValue.trim()) {
      loadEnrichmentRequirements(supplierValue)
    } else {
      setEnrichmentRequirements(null)
    }
  }, [supplierValue, loadEnrichmentRequirements])

  const onSubmit = async (data: PartFormData) => {
    console.log('🚀 onSubmit called!')
    console.log('onSubmit data:', data)
    console.log('onSubmit context:', { id, part, selectedCategories })

    if (!id || !part) {
      console.error('Missing id or part:', { id, part })
      return
    }

    setIsSaving(true)
    try {
      // Convert category IDs to category names
      const categoryNames = selectedCategories
        .map((categoryId) => {
          const category = categories.find((cat) => cat.id === categoryId)
          return category?.name
        })
        .filter(Boolean) as string[]

      console.log('Category conversion:', { selectedCategories, categoryNames })

      // Get the current image_url value from the form
      const currentImageUrl = watch('image_url')

      console.log('Image URL values:', {
        dataImageUrl: data.image_url,
        currentImageUrl,
        watchedValue: watch('image_url'),
      })

      const updateData: CreatePartRequest = {
        ...data,
        image_url: currentImageUrl,
        categories: categoryNames,
        additional_properties: additionalProperties,
        // Convert empty strings to undefined to prevent foreign key constraint errors
        location_id: data.location_id === '' ? undefined : data.location_id,
        supplier_url: data.supplier_url === '' ? undefined : data.supplier_url,
        product_url: data.product_url === '' ? undefined : data.product_url,
      }

      console.log('Sending update data:', updateData)

      await partsService.updatePart({ id, ...updateData })

      // Handle project assignments
      const currentProjectIds = part.projects?.map((p) => p.id) || []
      console.log('Project assignment debug:', {
        selectedProjects,
        currentProjectIds,
        part_projects: part.projects,
      })
      const projectsToAdd = selectedProjects.filter((pid) => !currentProjectIds.includes(pid))
      const projectsToRemove = currentProjectIds.filter((pid) => !selectedProjects.includes(pid))
      console.log('Project changes:', { projectsToAdd, projectsToRemove })

      // Add new project assignments
      for (const projectId of projectsToAdd) {
        await projectsService.addPartToProject(projectId, id)
      }

      // Remove deselected project assignments
      for (const projectId of projectsToRemove) {
        await projectsService.removePartFromProject(projectId, id)
      }

      toast.success('Part updated successfully')
      navigate(`/parts/${id}`)
    } catch (error) {
      console.error('Error updating part:', error)
      toast.error('Failed to update part')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!id || !part) return

    if (!confirm(`Are you sure you want to delete "${part.name}"? This action cannot be undone.`)) {
      return
    }

    setIsDeleting(true)
    try {
      await partsService.deletePart(id)
      toast.success('Part deleted successfully')
      navigate('/parts')
    } catch (error) {
      console.error('Error deleting part:', error)
      toast.error('Failed to delete part')
    } finally {
      setIsDeleting(false)
    }
  }

  const toggleCategory = (categoryId: string) => {
    const newSelected = selectedCategories.includes(categoryId)
      ? selectedCategories.filter((id) => id !== categoryId)
      : [...selectedCategories, categoryId]

    console.log('Category toggled:', { categoryId, newSelected })
    setSelectedCategories(newSelected)
    setValue('category_ids', newSelected)
  }

  const toggleProject = (projectId: string) => {
    const newSelected = selectedProjects.includes(projectId)
      ? selectedProjects.filter((id) => id !== projectId)
      : [...selectedProjects, projectId]

    console.log('Project toggled:', { projectId, newSelected })
    setSelectedProjects(newSelected)
  }

  const addProperty = () => {
    if (newPropertyKey.trim() && newPropertyValue.trim()) {
      setAdditionalProperties((prev) => ({
        ...prev,
        [newPropertyKey.trim()]: newPropertyValue.trim(),
      }))
      setNewPropertyKey('')
      setNewPropertyValue('')
    }
  }

  const removeProperty = (key: string) => {
    setAdditionalProperties((prev) => {
      const newProps = { ...prev }
      delete newProps[key]
      return newProps
    })
  }

  const handleCategoryAdded = async () => {
    try {
      const categoriesData = await categoriesService.getAll()
      setCategories(categoriesData)
      setShowAddCategoryModal(false)
    } catch (error) {
      console.error('Error reloading categories:', error)
      toast.error('Failed to reload categories')
    }
  }

  const handleLocationAdded = async () => {
    try {
      const locationsData = await locationsService.getAllLocations({ hide_auto_slots: false })
      setLocations(locationsData)
      setShowAddLocationModal(false)
    } catch (error) {
      console.error('Error reloading locations:', error)
      toast.error('Failed to reload locations')
    }
  }

  const handleProjectAdded = async (createdProjectId?: string) => {
    try {
      const projectsData = await projectsService.getAllProjects()
      setProjects(projectsData)
      setShowAddProjectModal(false)

      // Auto-select the newly created project
      if (createdProjectId) {
        const newSelected = [...selectedProjects, createdProjectId]
        console.log('Auto-selecting newly created project:', { createdProjectId, newSelected })
        setSelectedProjects(newSelected)
        toast.success('Project added and automatically selected')
      }
    } catch (error) {
      console.error('Error reloading projects:', error)
      toast.error('Failed to reload projects')
    }
  }

  const updateProperty = (key: string, value: string) => {
    setAdditionalProperties((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!part) {
    return (
      <div className="text-center py-12">
        <Package className="mx-auto h-12 w-12 text-muted" />
        <h3 className="mt-2 text-sm font-medium text-secondary">Part not found</h3>
        <p className="mt-1 text-sm text-muted">The requested part could not be found.</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate(`/parts/${id}`)} className="btn btn-ghost p-2">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-primary">Edit Part</h1>
            <p className="text-secondary">{part.name}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="btn btn-danger flex items-center space-x-2"
          >
            <Trash2 className="w-4 h-4" />
            <span>{isDeleting ? 'Deleting...' : 'Delete'}</span>
          </button>
          <button
            type="button"
            onClick={() => {
              console.log('Save button clicked')
              console.log(
                'Form errors:',
                Object.keys(errors).length > 0
                  ? Object.fromEntries(
                      Object.entries(errors).map(([key, error]) => [key, error?.message])
                    )
                  : 'No errors'
              )
              console.log('Form isValid:', isValid)
              console.log('Form values:', watch())
              handleSubmit(onSubmit)()
            }}
            disabled={isSaving}
            className="btn btn-primary flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      {/* Debug Section */}
      {Object.keys(errors).length > 0 && (
        <div className="bg-error/10 border border-error/20 rounded-lg p-4">
          <h3 className="text-error font-medium mb-2">Form Validation Errors:</h3>
          <div className="text-error text-sm">
            {Object.entries(errors).map(([field, error]) => (
              <div key={field}>
                <strong>{field}:</strong> {error?.message || 'Unknown error'}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        {/* Hidden inputs to register enriched fields and preserve them on edit */}
        <input type="hidden" {...register('image_url')} />
        <input type="hidden" {...register('emoji')} />
        <input type="hidden" {...register('manufacturer')} />
        <input type="hidden" {...register('manufacturer_part_number')} />
        <input type="hidden" {...register('component_type')} />

        {/* Basic Information */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField label="Name" error={errors.name?.message} required>
              <input {...register('name')} className="input w-full" placeholder="Enter part name" />
            </FormField>

            <FormField label="Part Number" error={errors.part_number?.message}>
              <input
                {...register('part_number')}
                className="input w-full"
                placeholder="Enter part number"
              />
            </FormField>

            <FormField
              label="Description"
              error={errors.description?.message}
              className="md:col-span-2"
            >
              <textarea
                {...register('description')}
                rows={5}
                className="input w-full resize-none"
                placeholder="Enter part description"
              />
            </FormField>
          </div>
        </div>

        {/* Inventory Information */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Inventory Information</h2>
          <div className="space-y-6">
            {/* Quantity Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField label="Quantity" error={errors.quantity?.message} required>
                <input
                  {...register('quantity', { valueAsNumber: true })}
                  type="number"
                  min="0"
                  className="input w-full"
                  placeholder="0"
                />
              </FormField>

              <FormField label="Minimum Quantity" error={errors.minimum_quantity?.message}>
                <input
                  {...register('minimum_quantity', { valueAsNumber: true })}
                  type="number"
                  min="0"
                  className="input w-full"
                  placeholder="0"
                />
              </FormField>
            </div>

            {/* Location - Full Width */}
            <HierarchicalLocationPicker
              value={watch('location_id')}
              onChange={(locationId) => {
                if (!locationId) {
                  setValue('location_id', '')
                } else {
                  setValue('location_id', locationId)
                }
              }}
              label="Location"
              error={errors.location_id?.message}
            />
          </div>
        </div>

        {/* Categories */}
        <div className="card p-6">
          <CategorySelector
            categories={categories}
            selectedCategories={selectedCategories}
            onToggleCategory={toggleCategory}
            onAddNewCategory={() => setShowAddCategoryModal(true)}
            label="Categories"
            description="Select categories that apply to this part"
            showAddButton={true}
            layout="checkboxes"
          />
        </div>

        {/* Projects */}
        <div className="card p-6">
          <FormField label="Projects" description="Assign this part to one or more projects">
            <CustomSelect
              multiSelect={true}
              selectedValues={selectedProjects}
              onMultiSelectChange={(values) => {
                console.log('Projects changed:', values)
                setSelectedProjects(values)
              }}
              options={projects.map((project) => ({
                value: project.id,
                label: project.name,
              }))}
              placeholder="Select projects..."
              searchable={true}
              searchPlaceholder="Search projects..."
              onAddNew={() => setShowAddProjectModal(true)}
              addNewLabel="Add New Project"
            />
          </FormField>
        </div>

        {/* Supplier Information */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Supplier Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              label="Supplier"
              error={errors.supplier?.message}
              description="Select a configured supplier or enter a custom one"
            >
              <SupplierSelector
                value={watch('supplier') || ''}
                onChange={(value) => setValue('supplier', value)}
                error={errors.supplier?.message}
                placeholder="Select supplier..."
              />
            </FormField>

            <FormField
              label="Supplier Part Number"
              error={errors.supplier_part_number?.message}
              description="Supplier's part number for API calls (e.g., LCSC: C25804, DigiKey: 296-1234-ND)"
            >
              <input
                {...register('supplier_part_number')}
                type="text"
                className="input w-full"
                placeholder="C25804, 296-1234-ND, etc."
              />
            </FormField>

            <FormField
              label="Supplier URL"
              error={errors.supplier_url?.message}
              description="Supplier homepage URL"
            >
              <input
                {...register('supplier_url')}
                type="url"
                className="input w-full"
                placeholder="https://supplier.com"
              />
            </FormField>

            <FormField
              label="Product URL"
              error={errors.product_url?.message}
              description="Specific product page URL"
            >
              <input
                {...register('product_url')}
                type="url"
                className="input w-full"
                placeholder="https://supplier.com/product/12345"
              />
            </FormField>
          </div>

          {/* Enrichment Requirements Display */}
          {watch('supplier') && (
            <div className="mt-6 border-t border-border pt-6">
              {loadingRequirements ? (
                <div className="flex items-center gap-2 text-secondary">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  <span className="text-sm">Loading enrichment requirements...</span>
                </div>
              ) : enrichmentRequirements ? (
                <div className="space-y-4">
                  <div className="flex items-start gap-2">
                    <Info className="w-5 h-5 text-info mt-0.5 flex-shrink-0" />
                    <div>
                      <h3 className="text-sm font-semibold text-primary mb-1">
                        Enrichment Requirements for {enrichmentRequirements.display_name}
                      </h3>
                      <p className="text-xs text-secondary mb-3">
                        {enrichmentRequirements.description}
                      </p>
                    </div>
                  </div>

                  {/* Required Fields */}
                  {enrichmentRequirements.required_fields &&
                    enrichmentRequirements.required_fields.length > 0 && (
                      <div className="bg-error/5 border border-error/20 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <AlertCircle className="w-4 h-4 text-error" />
                          <h4 className="text-sm font-semibold text-error">
                            Required Fields for Enrichment
                          </h4>
                        </div>
                        <div className="space-y-4">
                          {enrichmentRequirements.required_fields.map((field) => {
                            // Get current value from part data or additional_properties
                            const getCurrentValue = () => {
                              if (!part) return ''
                              // Check top-level fields first
                              if (field.field_name === 'part_number') return part.part_number || ''
                              if (field.field_name === 'supplier_part_number')
                                return part.supplier_part_number || ''
                              if (field.field_name === 'manufacturer')
                                return (
                                  part.additional_properties?.manufacturer ||
                                  part.additional_properties?.Manufacturer ||
                                  ''
                                )
                              if (field.field_name === 'supplier') return part.supplier || ''
                              // Check additional_properties
                              return part.additional_properties?.[field.field_name] || ''
                            }

                            const currentValue = getCurrentValue()
                            const hasValue = !!currentValue

                            return (
                              <div key={field.field_name} className="space-y-2">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <label className="block text-sm font-medium text-primary mb-1">
                                      {field.display_name}
                                      {hasValue && (
                                        <CheckCircle className="w-4 h-4 text-success inline ml-2" />
                                      )}
                                    </label>
                                    <p className="text-xs text-secondary mb-2">
                                      {field.description}
                                    </p>
                                  </div>
                                </div>

                                {/* Show current value */}
                                {field.field_name === 'part_number' ? (
                                  <div className="text-sm p-2 bg-background-secondary rounded border border-border">
                                    <span className="text-muted">Current: </span>
                                    <span
                                      className={
                                        hasValue ? 'text-primary font-medium' : 'text-muted italic'
                                      }
                                    >
                                      {currentValue || 'Not set'}
                                    </span>
                                    <p className="text-xs text-muted mt-1">
                                      Edit in "Basic Information" section above
                                    </p>
                                  </div>
                                ) : field.field_name === 'supplier' ? (
                                  <div className="text-sm p-2 bg-background-secondary rounded border border-border">
                                    <span className="text-muted">Current: </span>
                                    <span
                                      className={
                                        hasValue ? 'text-primary font-medium' : 'text-muted italic'
                                      }
                                    >
                                      {currentValue || 'Selected above'}
                                    </span>
                                  </div>
                                ) : (
                                  <div className="space-y-1">
                                    <div className="text-sm p-2 bg-background-secondary rounded border border-border">
                                      <span className="text-muted">Current: </span>
                                      <span
                                        className={
                                          hasValue
                                            ? 'text-primary font-medium'
                                            : 'text-muted italic'
                                        }
                                      >
                                        {currentValue || 'Not set'}
                                      </span>
                                    </div>
                                    <input
                                      type="text"
                                      value={additionalProperties[field.field_name] || ''}
                                      onChange={(e) =>
                                        setAdditionalProperties((prev) => ({
                                          ...prev,
                                          [field.field_name]: e.target.value,
                                        }))
                                      }
                                      placeholder={
                                        field.example ||
                                        `Enter ${field.display_name.toLowerCase()}...`
                                      }
                                      className="input w-full text-sm"
                                    />
                                  </div>
                                )}

                                {field.example && (
                                  <p className="text-xs text-muted">
                                    Example:{' '}
                                    <code className="bg-background-tertiary px-1 rounded">
                                      {field.example}
                                    </code>
                                  </p>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}

                  {/* Recommended Fields */}
                  {enrichmentRequirements.recommended_fields &&
                    enrichmentRequirements.recommended_fields.length > 0 && (
                      <div className="bg-info/5 border border-info/20 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <HelpCircle className="w-4 h-4 text-info" />
                          <h4 className="text-sm font-semibold text-info">
                            Recommended Fields (Optional)
                          </h4>
                        </div>
                        <div className="space-y-4">
                          {enrichmentRequirements.recommended_fields.map((field) => {
                            // Get current value from part data or additional_properties
                            const getCurrentValue = () => {
                              if (!part) return ''
                              // Check top-level fields first
                              if (field.field_name === 'description') return part.description || ''
                              if (field.field_name === 'part_number') return part.part_number || ''
                              if (field.field_name === 'manufacturer')
                                return (
                                  part.additional_properties?.manufacturer ||
                                  part.additional_properties?.Manufacturer ||
                                  ''
                                )
                              // Check additional_properties
                              return part.additional_properties?.[field.field_name] || ''
                            }

                            const currentValue = getCurrentValue()
                            const hasValue = !!currentValue

                            return (
                              <div key={field.field_name} className="space-y-2">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <label className="block text-sm font-medium text-primary mb-1">
                                      {field.display_name}
                                      {hasValue && (
                                        <CheckCircle className="w-4 h-4 text-success inline ml-2" />
                                      )}
                                    </label>
                                    <p className="text-xs text-secondary mb-2">
                                      {field.description}
                                    </p>
                                  </div>
                                </div>

                                {/* Show current value */}
                                {field.field_name === 'part_number' ||
                                field.field_name === 'description' ? (
                                  <div className="text-sm p-2 bg-background-secondary rounded border border-border">
                                    <span className="text-muted">Current: </span>
                                    <span
                                      className={
                                        hasValue ? 'text-primary font-medium' : 'text-muted italic'
                                      }
                                    >
                                      {currentValue || 'Not set'}
                                    </span>
                                    <p className="text-xs text-muted mt-1">
                                      Edit in "Basic Information" section above
                                    </p>
                                  </div>
                                ) : (
                                  <div className="space-y-1">
                                    <div className="text-sm p-2 bg-background-secondary rounded border border-border">
                                      <span className="text-muted">Current: </span>
                                      <span
                                        className={
                                          hasValue
                                            ? 'text-primary font-medium'
                                            : 'text-muted italic'
                                        }
                                      >
                                        {currentValue || 'Not set'}
                                      </span>
                                    </div>
                                    <input
                                      type="text"
                                      value={additionalProperties[field.field_name] || ''}
                                      onChange={(e) =>
                                        setAdditionalProperties((prev) => ({
                                          ...prev,
                                          [field.field_name]: e.target.value,
                                        }))
                                      }
                                      placeholder={
                                        field.example ||
                                        `Enter ${field.display_name.toLowerCase()}...`
                                      }
                                      className="input w-full text-sm"
                                    />
                                  </div>
                                )}

                                {field.example && (
                                  <p className="text-xs text-muted">
                                    Example:{' '}
                                    <code className="bg-background-tertiary px-1 rounded">
                                      {field.example}
                                    </code>
                                  </p>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}

                  {/* Success message if no requirements */}
                  {(!enrichmentRequirements.required_fields ||
                    enrichmentRequirements.required_fields.length === 0) &&
                    (!enrichmentRequirements.recommended_fields ||
                      enrichmentRequirements.recommended_fields.length === 0) && (
                      <div className="bg-success/10 border border-success/20 rounded-lg p-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-success" />
                          <p className="text-sm text-success">
                            No additional fields required for enrichment from this supplier.
                          </p>
                        </div>
                      </div>
                    )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Resources */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Resources</h2>
          <div className="space-y-6">
            <FormField
              label="Part Image"
              description="Upload, drag & drop, or paste an image of the part (max 5MB)"
            >
              <ImageUpload
                onImageUploaded={(url) => setValue('image_url', url)}
                currentImageUrl={watch('image_url')}
                placeholder="Upload part image"
                className="w-full"
              />
            </FormField>

            <FormField
              label="Part Emoji"
              description="Select an emoji icon for this part (can be used on printer labels)"
            >
              <EmojiPicker
                value={watch('emoji') || undefined}
                onChange={(selectedEmoji) => setValue('emoji', selectedEmoji || '')}
                placeholder="Select emoji icon..."
              />
            </FormField>
          </div>
        </div>

        {/* Additional Properties */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-primary">Additional Properties</h2>
              <TooltipIcon
                tooltip={
                  <div className="space-y-2">
                    <p className="font-medium">Custom Part Metadata</p>
                    <p>
                      Store technical specifications, part ratings, or any other relevant
                      information specific to this component.
                    </p>
                    <p className="text-sm opacity-90">
                      <strong>Examples:</strong>
                    </p>
                    <ul className="text-sm opacity-90 list-disc list-inside space-y-1">
                      <li>Resistance: 10kΩ ±5%</li>
                      <li>Voltage Rating: 25V</li>
                      <li>Package: SMD 0805</li>
                      <li>Temperature Range: -40°C to 125°C</li>
                    </ul>
                    <p className="text-sm opacity-90 mt-2">
                      These properties are automatically populated during CSV imports with
                      enrichment data from your suppliers.
                    </p>
                  </div>
                }
                variant="help"
                position="right"
              />
            </div>
            <span className="text-sm text-secondary bg-background-secondary px-2 py-1 rounded">
              {Object.keys(additionalProperties).length} properties
            </span>
          </div>

          {/* Existing Properties */}
          {Object.keys(additionalProperties).length > 0 && (
            <div className="space-y-3 mb-6">
              {Object.entries(additionalProperties).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center gap-3 p-3 bg-background-secondary rounded-lg"
                >
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-secondary mb-1">Property Name</label>
                      <input
                        type="text"
                        value={key}
                        readOnly
                        className="input-sm w-full font-mono bg-background-tertiary"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-secondary mb-1">Value</label>
                      <input
                        type="text"
                        value={typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        onChange={(e) => updateProperty(key, e.target.value)}
                        className="input-sm w-full"
                        style={{ color: 'black', backgroundColor: 'white' }}
                      />
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeProperty(key)}
                    className="p-2 text-error hover:text-error hover:bg-error/10 rounded-lg transition-colors"
                    title="Remove property"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add New Property */}
          <div className="border-t border-border pt-6">
            <h3 className="text-sm font-medium text-primary mb-3 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Add New Property
            </h3>
            <div className="flex gap-3">
              <div className="flex-1">
                <input
                  type="text"
                  value={newPropertyKey}
                  onChange={(e) => setNewPropertyKey(e.target.value)}
                  placeholder="Property name (e.g., resistance, voltage)"
                  className="input w-full"
                />
              </div>
              <div className="flex-1">
                <input
                  type="text"
                  value={newPropertyValue}
                  onChange={(e) => setNewPropertyValue(e.target.value)}
                  placeholder="Value (e.g., 10kΩ, 5V)"
                  className="input w-full"
                />
              </div>
              <button
                type="button"
                onClick={addProperty}
                disabled={!newPropertyKey.trim() || !newPropertyValue.trim()}
                className="btn btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Modals */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryAdded}
        existingCategories={categories.map((cat) => cat.name)}
      />

      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationAdded}
      />

      {selectedContainer && (
        <ContainerSlotPickerModal
          isOpen={showSlotPickerModal}
          onClose={() => setShowSlotPickerModal(false)}
          containerLocation={selectedContainer}
          currentSlotId={watch('location_id')}
          onSlotSelect={(slotId) => {
            setValue('location_id', slotId)
            setShowSlotPickerModal(false)
          }}
        />
      )}

      <AddProjectModal
        isOpen={showAddProjectModal}
        onClose={() => setShowAddProjectModal(false)}
        onSuccess={handleProjectAdded}
        existingProjects={projects.map((proj) => proj.name)}
      />
    </div>
  )
}

export default EditPartPage
