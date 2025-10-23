import { useState, useEffect, useCallback } from 'react'
import CrudModal from '@/components/ui/CrudModal'
import { FormInput, FormField, LocationTreeSelector } from '@/components/forms'
import { CustomSelect } from '@/components/ui/CustomSelect'
import EmojiPicker from '@/components/ui/EmojiPicker'
import ImageUpload from '@/components/ui/ImageUpload'
import { useModalFormWithValidation } from '@/hooks/useFormWithValidation'
import { locationFormSchema, type LocationFormData } from '@/schemas/locations'
import { locationsService } from '@/services/locations.service'
import type { Location } from '@/types/locations'
import toast from 'react-hot-toast'
import { AlertCircle, X } from 'lucide-react'

interface AddLocationModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  defaultParentId?: string
}

// Draft persistence constants
const LOCATION_DRAFT_KEY = 'makermatrix_location_draft'
const DRAFT_MAX_AGE_MS = 24 * 60 * 60 * 1000 // 24 hours

interface LocationDraft {
  formData: Partial<LocationFormData>
  imageUrl: string
  timestamp: number
}

const AddLocationModal = ({
  isOpen,
  onClose,
  onSuccess,
  defaultParentId,
}: AddLocationModalProps) => {
  const [parentLocations, setParentLocations] = useState<Location[]>([])
  const [loadingData, setLoadingData] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>('')
  const [hasDraft, setHasDraft] = useState(false)
  const [showDraftBanner, setShowDraftBanner] = useState(false)

  const locationTypes = [
    { value: 'standard', label: 'Standard' },
    { value: 'single_part', label: 'Single Part (e.g., SMD Cassette)' },
    { value: 'warehouse', label: 'Warehouse' },
    { value: 'toolbox', label: 'Toolbox' },
    { value: 'room', label: 'Room' },
    { value: 'shelf', label: 'Shelf' },
    { value: 'drawer', label: 'Drawer' },
    { value: 'bin', label: 'Bin' },
    { value: 'cabinet', label: 'Cabinet' },
    { value: 'building', label: 'Building' },
    { value: 'container', label: 'Container' },
  ]

  // Form with validation
  const form = useModalFormWithValidation<LocationFormData>({
    schema: locationFormSchema,
    isOpen,
    onClose,
    defaultValues: {
      name: '',
      description: '',
      location_type: 'standard',
      parent_id: defaultParentId || undefined,
      image_url: undefined,
      emoji: undefined,
      image_file: undefined,
      slot_count: 10,
      slot_naming_pattern: 'Slot {n}',
      slot_layout_type: 'simple' as any,
      grid_rows: 2,
      grid_columns: 5,
    },
    onSubmit: handleFormSubmit,
    onSuccess: () => {
      clearDraft() // Clear draft on successful creation
      onSuccess()
      handleClose()
    },
    successMessage: 'Location created successfully',
    transformData: (data) => {
      // Transform form data to API format
      const { image_file, ...apiData } = data

      // Only include container slot fields if location_type is 'container'
      if (data.location_type !== 'container') {
        const {
          slot_count,
          slot_naming_pattern,
          slot_layout_type,
          grid_rows,
          grid_columns,
          ...nonContainerData
        } = apiData
        return {
          ...nonContainerData,
          name: data.name.trim(),
          parent_id: data.parent_id || undefined,
          location_type: data.location_type || 'standard',
        }
      }

      return {
        ...apiData,
        name: data.name.trim(),
        parent_id: data.parent_id || undefined,
        location_type: data.location_type || 'standard',
      }
    },
  })

  // Container slot state - use form state instead of local state
  const slotLayoutType =
    (form.watch('slot_layout_type') as unknown as 'simple' | 'grid') || 'simple'
  const slotCount = (form.watch('slot_count') as unknown as number) || 10
  const gridRows = (form.watch('grid_rows') as unknown as number) || 2
  const gridColumns = (form.watch('grid_columns') as unknown as number) || 5
  const namingPattern = (form.watch('slot_naming_pattern') as unknown as string) || 'Slot {n}'

  // Check if current location type is container
  const isContainer = (form.watch('location_type') as unknown as string) === 'container'

  // Draft Management Functions
  const saveDraft = useCallback(() => {
    const formValues = form.getValues()
    const draft: LocationDraft = {
      formData: formValues,
      imageUrl,
      timestamp: Date.now(),
    }
    localStorage.setItem(LOCATION_DRAFT_KEY, JSON.stringify(draft))
  }, [form, imageUrl])

  const loadDraft = useCallback(() => {
    try {
      const stored = localStorage.getItem(LOCATION_DRAFT_KEY)
      if (!stored) return null

      const draft: LocationDraft = JSON.parse(stored)

      // Check if draft is too old
      if (Date.now() - draft.timestamp > DRAFT_MAX_AGE_MS) {
        localStorage.removeItem(LOCATION_DRAFT_KEY)
        return null
      }

      return draft
    } catch (error) {
      console.error('Error loading draft:', error)
      return null
    }
  }, [])

  const clearDraft = useCallback(() => {
    localStorage.removeItem(LOCATION_DRAFT_KEY)
    setHasDraft(false)
    setShowDraftBanner(false)
  }, [])

  const restoreDraft = useCallback(() => {
    const draft = loadDraft()
    if (draft) {
      // Restore form values
      Object.entries(draft.formData).forEach(([key, value]) => {
        if (value !== undefined) {
          form.setValue(key as any, value as any)
        }
      })

      // Restore image URL
      if (draft.imageUrl) {
        setImageUrl(draft.imageUrl)
      }

      toast.success('Draft restored')
      setShowDraftBanner(false)
    }
  }, [form, loadDraft])

  const discardDraft = useCallback(() => {
    clearDraft()
    toast.success('Draft discarded')
  }, [clearDraft])

  // Check for draft when modal opens
  useEffect(() => {
    if (isOpen) {
      loadParentLocations()

      // Set the default parent if provided
      if (defaultParentId) {
        form.setValue('parent_id', defaultParentId)
      }

      // Check for existing draft
      const draft = loadDraft()
      if (draft && draft.formData.name) {
        setHasDraft(true)
        setShowDraftBanner(true)
      }
    }
  }, [isOpen, defaultParentId, loadDraft])

  // Auto-save draft when form changes (debounced)
  useEffect(() => {
    if (!isOpen) return

    const formValues = form.getValues()

    // Only save if there's meaningful content
    if (formValues.name && formValues.name.trim()) {
      const timeoutId = setTimeout(() => {
        saveDraft()
      }, 500) // 500ms debounce

      return () => clearTimeout(timeoutId)
    }
  }, [isOpen, form.watch(), saveDraft])

  const loadParentLocations = async () => {
    try {
      setLoadingData(true)
      const locations = await locationsService.getAllLocations()
      setParentLocations(locations)
    } catch {
      toast.error('Failed to load parent locations')
    } finally {
      setLoadingData(false)
    }
  }

  // Generate preview slot names - show ALL slots (no truncation)
  function generatePreviewSlots(
    layoutType: 'simple' | 'grid',
    count: number,
    rows: number,
    cols: number,
    pattern: string
  ): string[] | string[][] {
    if (layoutType === 'simple') {
      // Return flat array for simple layout
      const preview: string[] = []
      for (let i = 1; i <= count; i++) {
        preview.push(pattern.replace('{n}', String(i)))
      }
      return preview
    } else {
      // Return 2D array for grid layout (rows of columns)
      const grid: string[][] = []
      let n = 1
      for (let r = 1; r <= rows; r++) {
        const row: string[] = []
        for (let c = 1; c <= cols; c++) {
          const name = pattern
            .replace('{n}', String(n))
            .replace('{row}', String(r))
            .replace('{col}', String(c))
          row.push(name)
          n++
        }
        grid.push(row)
      }
      return grid
    }
  }

  // Handle form submission
  async function handleFormSubmit(data: LocationFormData) {
    // Check for duplicate names at the same level
    const siblingLocations = data.parent_id
      ? parentLocations.filter((loc) => loc.parent_id === data.parent_id)
      : parentLocations.filter((loc) => !loc.parent_id)

    if (siblingLocations.some((loc) => loc.name.toLowerCase() === data.name.toLowerCase().trim())) {
      throw new Error('A location with this name already exists at this level')
    }

    // Create location with image URL and container data
    const locationData: any = {
      ...data,
      name: data.name.trim(),
      parent_id: data.parent_id || undefined,
      location_type: data.location_type || 'standard',
      image_url: imageUrl || undefined,
    }

    // Add container slot configuration if it's a container
    if (isContainer) {
      locationData.slot_layout_type = slotLayoutType
      locationData.slot_naming_pattern = namingPattern

      if (slotLayoutType === 'simple') {
        locationData.slot_count = slotCount
      } else if (slotLayoutType === 'grid') {
        locationData.slot_count = gridRows * gridColumns
        locationData.grid_rows = gridRows
        locationData.grid_columns = gridColumns
      }
    }

    return await locationsService.createLocation(locationData)
  }

  const handleClose = () => {
    // Don't clear draft on close - it will be available for restore
    setImageUrl('')
    form.reset()
    setShowDraftBanner(false)
    onClose()
  }

  // Wrap the original onSuccess to clear draft on successful creation
  const handleSuccessWithDraftClear = () => {
    clearDraft()
    onSuccess()
  }

  // Build hierarchical display for parent locations
  const buildLocationHierarchy = (
    locations: Location[]
  ): Array<{ id: string; name: string; level: number }> => {
    const result: Array<{ id: string; name: string; level: number }> = []

    // Create a map for quick lookup
    const locationMap = new Map<string, Location>()
    locations.forEach((loc) => locationMap.set(loc.id, loc))

    const addLocation = (location: Location, level: number = 0) => {
      result.push({
        id: location.id,
        name: location.name,
        level,
      })

      // Find children in the flat list
      const children = locations.filter((loc) => loc.parent_id === location.id)
      children
        .sort((a, b) => a.name.localeCompare(b.name)) // Sort alphabetically
        .forEach((child) => addLocation(child, level + 1))
    }

    // Start with root locations (no parent) and sort them
    const rootLocations = locations
      .filter((loc) => !loc.parent_id)
      .sort((a, b) => a.name.localeCompare(b.name))

    rootLocations.forEach((loc) => addLocation(loc))

    return result
  }

  const hierarchicalLocations = buildLocationHierarchy(parentLocations)

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add New Location"
      size="xl"
      mode="create"
      onSubmit={form.onSubmit}
      loading={form.loading}
      loadingText="Creating..."
      submitText="Create Location"
    >
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-theme-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <>
          {/* Draft Banner */}
          {showDraftBanner && hasDraft && (
            <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  You have unsaved work from a previous session
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                  Would you like to restore your draft or start fresh?
                </p>
                <div className="flex gap-2 mt-3">
                  <button
                    type="button"
                    onClick={restoreDraft}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-yellow-600 hover:bg-yellow-700 rounded transition-colors"
                  >
                    Restore Draft
                  </button>
                  <button
                    type="button"
                    onClick={discardDraft}
                    className="px-3 py-1.5 text-xs font-medium text-yellow-800 dark:text-yellow-200 bg-yellow-100 dark:bg-yellow-900/40 hover:bg-yellow-200 dark:hover:bg-yellow-900/60 rounded transition-colors"
                  >
                    Discard Draft
                  </button>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowDraftBanner(false)}
                className="p-1 text-yellow-600 dark:text-yellow-500 hover:text-yellow-800 dark:hover:text-yellow-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-4">
            {/* Left Column - Main Fields (2/3 width) */}
            <div className="lg:col-span-2 space-y-6">
              {/* Name and Type */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormInput
                  label="Location Name"
                  placeholder="Enter location name"
                  required
                  registration={form.register('name')}
                  error={form.getFieldError('name')}
                />

                <FormField
                  label="Location Type"
                  description="Select from common types or create a custom type"
                  error={form.getFieldError('location_type')}
                >
                  <CustomSelect
                    value={(form.watch('location_type') as unknown as string) || 'standard'}
                    onChange={(value) => form.setValue('location_type', value as unknown as string)}
                    options={locationTypes}
                    placeholder="Select or type a custom type"
                    searchPlaceholder="Type to search or create custom type..."
                    error={form.getFieldError('location_type')}
                    allowCustom={true}
                    customLabel="Create custom type"
                  />
                </FormField>
              </div>

              {/* Description */}
              <FormInput
                label="Description"
                placeholder="Enter a description (optional)"
                registration={form.register('description')}
                error={form.getFieldError('description')}
              />

              {/* Parent Location */}
              <FormField
                label="Parent Location"
                description="Select a parent location to create a hierarchy (optional)"
              >
                <LocationTreeSelector
                  selectedLocationId={form.watch('parent_id') as unknown as string | undefined}
                  onLocationSelect={(locationId) =>
                    form.setValue('parent_id', locationId || undefined)
                  }
                  showAddButton={false}
                  compact={true}
                />
              </FormField>

              {/* Preview of full path */}
              {form.watch('parent_id') && (
                <div className="p-3 bg-theme-secondary rounded-md border border-theme-primary">
                  <p className="text-sm text-theme-muted mb-1">Full path will be:</p>
                  <p className="text-sm font-medium text-theme-primary">
                    {(() => {
                      const parentId = form.watch('parent_id') as unknown as string | undefined
                      const parent = parentLocations.find((loc) => loc.id === parentId)
                      if (parent) {
                        // Build full path from flat list
                        const buildPath = (loc: Location): string => {
                          if (loc.parent_id) {
                            const parentLoc = parentLocations.find((p) => p.id === loc.parent_id)
                            if (parentLoc) {
                              return buildPath(parentLoc) + ' → ' + loc.name
                            }
                          }
                          return loc.name
                        }
                        return (
                          buildPath(parent) +
                          ' → ' +
                          ((form.watch('name') as unknown as string) || '[New Location]')
                        )
                      }
                      return (form.watch('name') as unknown as string) || '[New Location]'
                    })()}
                  </p>
                </div>
              )}

              {/* Container Slot Configuration */}
              {isContainer && (
                <div className="p-4 bg-theme-secondary rounded-md border border-theme-primary space-y-4">
                  <h4 className="text-base font-semibold text-theme-primary">
                    Container Slot Configuration
                  </h4>

                  {/* Layout Type Selector */}
                  <FormField label="Layout Type">
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          value="simple"
                          checked={slotLayoutType === 'simple'}
                          onChange={(e) => {
                            form.setValue('slot_layout_type', 'simple' as any)
                            form.setValue('slot_naming_pattern', 'Slot {n}')
                          }}
                          className="w-4 h-4 text-primary focus:ring-primary"
                        />
                        <span className="text-sm text-theme-primary">Simple (numbered slots)</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          value="grid"
                          checked={slotLayoutType === 'grid'}
                          onChange={(e) => {
                            form.setValue('slot_layout_type', 'grid' as any)
                            form.setValue('slot_naming_pattern', 'R{row}-C{col}')
                          }}
                          className="w-4 h-4 text-primary focus:ring-primary"
                        />
                        <span className="text-sm text-theme-primary">Grid (rows × columns)</span>
                      </label>
                    </div>
                  </FormField>

                  {/* Simple Mode - Slot Count */}
                  {slotLayoutType === 'simple' && (
                    <FormInput
                      label="Number of Slots"
                      type="number"
                      min={1}
                      max={200}
                      value={slotCount.toString()}
                      onChange={(e) => form.setValue('slot_count', Number(e.target.value))}
                    />
                  )}

                  {/* Grid Mode - Rows and Columns */}
                  {slotLayoutType === 'grid' && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <FormInput
                          label="Rows"
                          type="number"
                          min={1}
                          max={20}
                          value={gridRows.toString()}
                          onChange={(e) => {
                            const rows = Number(e.target.value)
                            form.setValue('grid_rows', rows)
                            form.setValue('slot_count', rows * gridColumns)
                          }}
                        />
                        <FormInput
                          label="Columns"
                          type="number"
                          min={1}
                          max={20}
                          value={gridColumns.toString()}
                          onChange={(e) => {
                            const cols = Number(e.target.value)
                            form.setValue('grid_columns', cols)
                            form.setValue('slot_count', gridRows * cols)
                          }}
                        />
                      </div>
                      <div className="p-2 bg-theme-elevated rounded text-sm text-theme-secondary">
                        Total slots:{' '}
                        <strong className="text-theme-primary">{gridRows * gridColumns}</strong>
                      </div>
                    </div>
                  )}

                  {/* Naming Pattern */}
                  <FormInput
                    label="Slot Naming Pattern"
                    value={namingPattern}
                    onChange={(e) => form.setValue('slot_naming_pattern', e.target.value)}
                    placeholder={slotLayoutType === 'grid' ? 'R{row}-C{col}' : 'Slot {n}'}
                    description={
                      slotLayoutType === 'grid'
                        ? 'Use {n} for number, {row} for row, {col} for column'
                        : 'Use {n} for slot number'
                    }
                  />

                  {/* Live Preview - Show all slots with scrolling */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-theme-primary">
                      Preview ({slotLayoutType === 'simple' ? slotCount : gridRows * gridColumns}{' '}
                      slots):
                    </label>
                    <div className="max-h-48 overflow-y-auto p-3 bg-theme-elevated rounded border border-theme-primary">
                      {slotLayoutType === 'simple' ? (
                        // Simple layout - flat wrap
                        <div className="flex flex-wrap gap-2">
                          {(
                            generatePreviewSlots(
                              slotLayoutType,
                              slotCount,
                              gridRows,
                              gridColumns,
                              namingPattern
                            ) as string[]
                          ).map((name, i) => (
                            <span
                              key={i}
                              className="px-2 py-1 text-xs rounded bg-primary/20 text-primary border border-primary/30"
                            >
                              {name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        // Grid layout - display as rows
                        <div className="space-y-2">
                          {(
                            generatePreviewSlots(
                              slotLayoutType,
                              slotCount,
                              gridRows,
                              gridColumns,
                              namingPattern
                            ) as string[][]
                          ).map((row, rowIdx) => (
                            <div key={rowIdx} className="flex gap-2 flex-wrap">
                              {row.map((name, colIdx) => (
                                <span
                                  key={colIdx}
                                  className="px-2 py-1 text-xs rounded bg-primary/20 text-primary border border-primary/30"
                                >
                                  {name}
                                </span>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column - Visual Identifiers (1/3 width) */}
            <div className="space-y-6">
              {/* Image Upload */}
              <FormField label="Location Image">
                <ImageUpload
                  onImageUploaded={setImageUrl}
                  currentImageUrl={imageUrl}
                  placeholder="Upload location image"
                  className="w-full"
                />
              </FormField>

              {/* Emoji Picker */}
              <FormField
                label="Location Emoji"
                description="Choose an emoji to identify this location"
              >
                <EmojiPicker
                  value={(form.watch('emoji') as unknown as string) || undefined}
                  onChange={(emoji) => form.setValue('emoji', emoji)}
                  placeholder="Click to select an emoji..."
                />
              </FormField>
            </div>
          </div>
        </>
      )}
    </CrudModal>
  )
}

export default AddLocationModal
