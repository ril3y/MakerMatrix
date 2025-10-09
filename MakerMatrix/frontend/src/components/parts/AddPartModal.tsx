import { useState, useEffect } from 'react'
import { Save, Package, Plus, X, Tag, MapPin, Hash, ChevronDown } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import ImageUpload from '@/components/ui/ImageUpload'
import EmojiPicker from '@/components/ui/EmojiPicker'
import { CustomSelect } from '@/components/ui/CustomSelect'
import LocationTreeSelector from '@/components/ui/LocationTreeSelector'
import SupplierSelector from '@/components/ui/SupplierSelector'
import { TooltipIcon } from '@/components/ui/Tooltip'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import AddProjectModal from '@/components/projects/AddProjectModal'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { projectsService } from '@/services/projects.service'
import { tasksService } from '@/services/tasks.service'
import supplierService from '@/services/supplier.service'
import { dynamicSupplierService } from '@/services/dynamic-supplier.service'
import type { CreatePartRequest } from '@/types/parts'
import type { Location, Category } from '@/types/parts'
import type { Project } from '@/types/projects'
import toast from 'react-hot-toast'

interface AddPartModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AddPartModal = ({ isOpen, onClose, onSuccess }: AddPartModalProps) => {
  const [formData, setFormData] = useState<CreatePartRequest>({
    name: '',
    part_number: '',
    description: '',
    quantity: 0,
    minimum_quantity: 0,
    supplier: '',
    supplier_url: '',
    product_url: '',
    supplier_part_number: '',
    location_id: '',
    categories: [],
    additional_properties: {},
  })

  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])
  const [customProperties, setCustomProperties] = useState<Array<{ key: string; value: string }>>(
    []
  )
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>('')
  const [emoji, setEmoji] = useState<string | null>(null)

  // Supplier required fields for enrichment
  const [supplierRequiredFields, setSupplierRequiredFields] = useState<CredentialFieldDefinition[]>(
    []
  )
  const [loadingSupplierFields, setLoadingSupplierFields] = useState(false)
  const [configuredSuppliers, setConfiguredSuppliers] = useState<string[]>([])
  const [availableSuppliers, setAvailableSuppliers] = useState<string[]>([]) // Suppliers in registry
  const [suppliersWithEnrichment, setSuppliersWithEnrichment] = useState<string[]>([]) // Suppliers with enrichment capabilities

  // Smart supplier detection state
  const [showConfigureSupplierPrompt, setShowConfigureSupplierPrompt] = useState(false)
  const [detectedSupplierInfo, setDetectedSupplierInfo] = useState<{
    name: string
    url: string
  } | null>(null)

  // Inline modal states
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false)
  const [showAddLocationModal, setShowAddLocationModal] = useState(false)
  const [showAddProjectModal, setShowAddProjectModal] = useState(false)
  const [isAdditionalPropsOpen, setIsAdditionalPropsOpen] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadData()
      // Load cached form data if available
      const cachedData = localStorage.getItem('addPartFormData')
      if (cachedData) {
        try {
          const parsed = JSON.parse(cachedData)
          setFormData(parsed.formData || formData)
          setSelectedCategories(parsed.selectedCategories || [])
          setSelectedProjects(parsed.selectedProjects || [])
          setCustomProperties(parsed.customProperties || [])
          setImageUrl(parsed.imageUrl || '')
          setEmoji(parsed.emoji || null)
          toast.success('Restored previous form data')
        } catch (error) {
          console.error('Failed to restore cached form data:', error)
        }
      }
    }
  }, [isOpen])

  // Fetch supplier enrichment requirements when supplier changes
  // Note: This is only for old-style suppliers with hardcoded requirements
  // New-style API suppliers use auto-enrichment from URL instead
  useEffect(() => {
    if (formData.supplier && formData.supplier.trim() && formData.supplier !== '__custom__') {
      const supplierLower = formData.supplier.toLowerCase()

      // Check if this is an API supplier (in registry) AND configured
      const isInRegistry = availableSuppliers.includes(supplierLower)
      const isConfigured = configuredSuppliers.includes(supplierLower)

      // Only try to load enrichment requirements for configured suppliers
      // The endpoint will return 404 for new-style suppliers, which is fine
      if (isInRegistry && isConfigured) {
        loadSupplierRequiredFields(formData.supplier)
      } else {
        // Either not an API supplier, or not configured yet - no enrichment requirements
        setSupplierRequiredFields([])
      }
    } else {
      setSupplierRequiredFields([])
    }
  }, [formData.supplier, configuredSuppliers, availableSuppliers])

  const loadData = async () => {
    try {
      setLoadingData(true)
      const [
        locationsData,
        categoriesData,
        projectsData,
        suppliersData,
        availableSuppliersData,
        importSuppliersData,
      ] = await Promise.all([
        locationsService.getAllLocations(),
        categoriesService.getAllCategories(),
        projectsService.getAllProjects(),
        supplierService.getSuppliers(true), // Get only enabled/configured suppliers
        dynamicSupplierService.getAvailableSuppliers(), // Get all available suppliers from registry
        fetch('/api/import/suppliers')
          .then((res) => res.json())
          .catch(() => ({ data: [] })), // Get enrichment capabilities
      ])
      setLocations(locationsData || [])
      setCategories(categoriesData || [])
      setProjects(projectsData || [])

      // Store configured supplier names for checking against custom suppliers
      const configuredNames = suppliersData.map((s) => s.supplier_name.toLowerCase())
      setConfiguredSuppliers(configuredNames)

      // Store available suppliers from registry - these are already lowercase strings
      const availableNames = Array.isArray(availableSuppliersData)
        ? availableSuppliersData.map((s) => s.toLowerCase())
        : []
      setAvailableSuppliers(availableNames)

      // Store suppliers with enrichment capabilities
      interface ImportSupplierData {
        name: string
        enrichment_available: boolean
      }
      const enrichmentNames = (importSuppliersData.data || [])
        .filter((s: ImportSupplierData) => s.enrichment_available === true)
        .map((s: ImportSupplierData) => s.name.toLowerCase())
      setSuppliersWithEnrichment(enrichmentNames)

      console.log('🔍 Smart Supplier Detection Setup:')
      console.log('  Configured suppliers:', configuredNames)
      console.log('  Available suppliers from registry:', availableNames)
      console.log('  Suppliers with enrichment:', enrichmentNames)
    } catch (error) {
      console.error('Failed to load data:', error)
      toast.error('Failed to load data')
      // Set empty arrays as fallbacks
      setLocations([])
      setCategories([])
      setProjects([])
      setConfiguredSuppliers([])
      setAvailableSuppliers([])
      setSuppliersWithEnrichment([])
    } finally {
      setLoadingData(false)
    }
  }

  const loadSupplierRequiredFields = async (supplierName: string) => {
    try {
      setLoadingSupplierFields(true)
      // Get enrichment requirements for the supplier (404 is expected for new-style suppliers)
      const response = await partsService.getSupplierEnrichmentRequirements(supplierName)

      console.log('Enrichment requirements response:', response)

      // Check if response and required_fields exist
      if (!response || !response.required_fields) {
        console.warn('No required fields in response:', response)
        setSupplierRequiredFields([])
        return
      }

      // Convert enrichment requirements to field definitions format
      interface EnrichmentFieldResponse {
        field_name: string
        display_name: string
        description?: string
        example?: string
        validation_pattern?: string
      }
      const requiredFields = response.required_fields.map((field: EnrichmentFieldResponse) => ({
        field: field.field_name,
        label: field.display_name,
        type: 'text', // Enrichment fields are typically text inputs
        required: true,
        description: field.description,
        placeholder: field.example
          ? `e.g., ${field.example}`
          : `Enter ${field.display_name.toLowerCase()}`,
        help_text: field.description,
        validation: field.validation_pattern ? { pattern: field.validation_pattern } : undefined,
      }))

      console.log('Converted required fields:', requiredFields)
      setSupplierRequiredFields(requiredFields)
    } catch (error) {
      // 404 errors are expected for new-style suppliers using dynamic patterns
      const err = error as { response?: { status?: number } }
      if (err.response?.status === 404) {
        console.log('No legacy enrichment requirements for this supplier (uses dynamic patterns)')
      } else {
        console.error('Failed to load supplier required fields:', error)
      }
      // Don't show error toast - supplier might not have enrichment requirements
      setSupplierRequiredFields([])
    } finally {
      setLoadingSupplierFields(false)
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Part name is required'
    }

    if (formData.quantity < 0) {
      newErrors.quantity = 'Quantity cannot be negative'
    }

    if (formData.minimum_quantity && formData.minimum_quantity < 0) {
      newErrors.minimum_quantity = 'Minimum quantity cannot be negative'
    }

    if (formData.supplier_url && !isValidUrl(formData.supplier_url)) {
      newErrors.supplier_url = 'Please enter a valid URL'
    }

    // Validate supplier-specific required fields (enrichment fields)
    supplierRequiredFields.forEach((field) => {
      const fieldName = field.field as keyof CreatePartRequest
      const value = formData[fieldName] as string
      if (!value || (typeof value === 'string' && !value.trim())) {
        newErrors[field.field] =
          `${field.label} is required for enrichment from ${formData.supplier}`
      }

      // Additional pattern validation if specified
      if (value && field.validation?.pattern) {
        const pattern = new RegExp(field.validation.pattern)
        if (!pattern.test(value)) {
          newErrors[field.field] =
            `${field.label} format is invalid (expected format like: ${field.placeholder || field.label})`
        }
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    console.log('Form submitted', formData)

    if (!validate()) {
      console.log('Validation failed', errors)
      return
    }

    try {
      setLoading(true)

      // Prepare properties object
      const properties: Record<string, unknown> = {}
      customProperties.forEach(({ key, value }) => {
        if (key.trim() && value.trim()) {
          properties[key.trim()] = value.trim()
        }
      })

      // Convert category IDs to category names
      const categoryNames = selectedCategories
        .map((categoryId) => {
          const category = categories.find((cat) => cat.id === categoryId)
          return category?.name
        })
        .filter(Boolean) as string[]

      const submitData: CreatePartRequest = {
        ...formData,
        image_url: imageUrl || undefined,
        emoji: emoji || undefined,
        categories: categoryNames,
        additional_properties: Object.keys(properties).length > 0 ? properties : undefined,
      }

      console.log('🚀 Creating part with data:', submitData)
      const createdPart = await partsService.createPart(submitData)
      toast.success('Part created successfully')

      // Associate part with selected projects
      if (selectedProjects.length > 0) {
        try {
          await Promise.all(
            selectedProjects.map((projectId) =>
              projectsService.addPartToProject(projectId, createdPart.id)
            )
          )
          console.log(`✅ Part associated with ${selectedProjects.length} project(s)`)
        } catch (error) {
          console.error('Failed to associate part with projects:', error)
          toast.error('Part created but failed to add to projects')
        }
      }

      // Auto-enrich only if supplier supports enrichment
      if (formData.supplier && formData.supplier.trim()) {
        // Check if supplier has enrichment capabilities
        const hasEnrichment = suppliersWithEnrichment.includes(formData.supplier.toLowerCase())

        if (hasEnrichment) {
          try {
            console.log(`Auto-enriching part ${createdPart.id} with supplier ${formData.supplier}`)
            const enrichmentTask = await tasksService.createPartEnrichmentTask({
              part_id: createdPart.id,
              supplier: formData.supplier.trim(),
              capabilities: ['get_part_details', 'fetch_datasheet', 'fetch_pricing_stock'],
              force_refresh: false,
            })
            toast.success(`Enrichment task created: ${enrichmentTask.data.name}`)
            console.log('Enrichment task created:', enrichmentTask.data)
          } catch (error) {
            console.error('Failed to create enrichment task:', error)
            toast.error('Part created but enrichment failed to start')
          }
        } else {
          console.log(
            `Supplier "${formData.supplier}" does not support enrichment - skipping auto-enrich`
          )
        }
      }

      console.log('Part created successfully, calling onSuccess and handleClose')
      clearFormData() // Clear cached data on successful submission
      onSuccess()
      handleClose()
    } catch (error) {
      console.error('Failed to create part:', error)
      const err = error as {
        response?: { data?: { detail?: string; message?: string }; status?: number }
        message?: string
      }
      console.error('Error response:', err.response?.data)
      console.error('Error status:', err.response?.status)

      const errorMessage =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to create part'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // Auto-save form data to localStorage whenever it changes
  useEffect(() => {
    if (isOpen) {
      const cacheData = {
        formData,
        selectedCategories,
        selectedProjects,
        customProperties,
        imageUrl,
        emoji,
      }
      localStorage.setItem('addPartFormData', JSON.stringify(cacheData))
    }
  }, [isOpen, formData, selectedCategories, selectedProjects, customProperties, imageUrl, emoji])

  const handleClose = () => {
    // Don't clear form data on close - keep it cached for next time
    // Only clear on successful submit or explicit clear

    // Close any open inline modals
    setShowAddCategoryModal(false)
    setShowAddLocationModal(false)
    setShowAddProjectModal(false)
    setShowConfigureSupplierPrompt(false)
    setDetectedSupplierInfo(null)

    onClose()
  }

  const clearFormData = () => {
    setFormData({
      name: '',
      part_number: '',
      description: '',
      quantity: 0,
      minimum_quantity: 0,
      supplier: '',
      supplier_url: '',
      supplier_part_number: '',
      location_id: '',
      categories: [],
      additional_properties: {},
    })
    setSelectedCategories([])
    setSelectedProjects([])
    setCustomProperties([])
    setErrors({})
    setImageUrl('')
    setEmoji(null)
    setSupplierRequiredFields([])
    localStorage.removeItem('addPartFormData')
  }

  const addCustomProperty = () => {
    setCustomProperties([...customProperties, { key: '', value: '' }])
    setIsAdditionalPropsOpen(true) // Auto-expand when adding a property
  }

  const updateCustomProperty = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...customProperties]
    updated[index][field] = value
    setCustomProperties(updated)
  }

  const removeCustomProperty = (index: number) => {
    setCustomProperties(customProperties.filter((_, i) => i !== index))
  }

  const extractDomainFromUrl = (url: string): string | null => {
    try {
      // Normalize input - add https:// if missing protocol
      let urlString = url.trim()
      if (!/^https?:\/\//i.test(urlString)) {
        if (urlString.includes('.')) {
          urlString = `https://${urlString}`
        } else {
          return null
        }
      }

      const urlObj = new URL(urlString)
      const hostname = urlObj.hostname

      // Remove common subdomains (www, shop, store, buy, order, checkout)
      const domain = hostname.replace(/^(www|shop|store|buy|order|checkout)\./i, '')

      // Extract base domain (e.g., "snapon.com" from "snapon.com" or remaining subdomains)
      const parts = domain.split('.')
      if (parts.length >= 2) {
        // Get the second-to-last part (e.g., "snapon" from "snapon.com")
        return parts[parts.length - 2]
      }

      // Fallback: just use the first part if no dots
      return parts[0]
    } catch {
      return null
    }
  }

  const handleSupplierUrlChange = async (url: string) => {
    // Extract base domain URL for supplier_url, keep full URL for product_url
    let baseUrl = url
    const fullUrl = url
    try {
      if (url.trim()) {
        const urlObj = new URL(url.startsWith('http') ? url : `https://${url}`)
        baseUrl = `${urlObj.protocol}//${urlObj.hostname}`
      }
    } catch {
      // If URL parsing fails, use the original URL
      baseUrl = url
    }

    setFormData({ ...formData, supplier_url: baseUrl, product_url: fullUrl })

    // If supplier field is empty and URL contains a domain, auto-populate supplier
    if (!formData.supplier && url.trim()) {
      const supplierName = extractDomainFromUrl(url)
      if (supplierName) {
        // Capitalize first letter
        const formattedName = supplierName.charAt(0).toUpperCase() + supplierName.slice(1)
        const supplierLower = supplierName.toLowerCase()

        // Set supplier field with both base URL and full product URL
        setFormData({ ...formData, supplier_url: baseUrl, product_url: fullUrl, supplier: formattedName })
        toast.success(`Auto-detected supplier: ${formattedName} from ${baseUrl}`)

        // Check supplier type
        const isInRegistry = availableSuppliers.includes(supplierLower)
        const isConfigured = configuredSuppliers.includes(supplierLower)

        console.log('🔍 Smart Supplier Detection Check:')
        console.log('  Detected supplier:', supplierLower)
        console.log('  Is in registry (REST supplier)?', isInRegistry)
        console.log('  Is configured?', isConfigured)
        console.log('  Available suppliers:', availableSuppliers)
        console.log('  Configured suppliers:', configuredSuppliers)

        // Path 1: REST supplier in registry
        if (isInRegistry) {
          // Path 1a: REST supplier but NOT configured
          if (!isConfigured) {
            console.log('✨ REST supplier not configured - showing configuration prompt')
            setDetectedSupplierInfo({ name: formattedName, url })
            setShowConfigureSupplierPrompt(true)
            return // Wait for user to choose configuration or simple supplier
          }

          // Path 1b: REST supplier AND configured - auto-enrich with dynamic patterns
          console.log('✅ REST supplier is configured - attempting dynamic auto-enrichment')
          await attemptDynamicEnrichment(url, supplierLower, formattedName)
        } else {
          // Path 2: NOT a REST supplier - create as simple supplier
          console.log('📎 Not a REST supplier - creating simple supplier')
          await createSimpleSupplier(supplierName, formattedName, url)
        }
      }
    }
  }

  /**
   * Extract field value from URL using dynamic patterns from supplier
   */
  const extractFieldFromUrl = (url: string, patterns: string[]): string | null => {
    try {
      for (const pattern of patterns) {
        const regex = new RegExp(pattern, 'i')
        const match = url.match(regex)
        if (match && match[1]) {
          return match[1]
        }
      }
      return null
    } catch (error) {
      console.error('Error extracting field from URL:', error)
      return null
    }
  }

  /**
   * Attempt auto-enrichment using dynamic URL pattern extraction
   */
  const attemptDynamicEnrichment = async (
    url: string,
    supplierName: string,
    formattedName: string
  ) => {
    try {
      console.log(`🔄 Loading enrichment field mappings for ${formattedName}...`)

      // Step 1: Get enrichment field mappings (URL patterns) from supplier
      const mappings = await dynamicSupplierService.getEnrichmentFieldMappings(supplierName)

      if (!mappings || mappings.length === 0) {
        console.warn(`No enrichment field mappings available for ${formattedName}`)
        return
      }

      console.log(`✅ Loaded ${mappings.length} field mapping(s):`, mappings)

      // Step 2: Extract field values from URL using patterns
      const extractedFields: Record<string, string> = {}
      let primaryFieldValue: string | null = null
      let primaryFieldName: string | null = null

      for (const mapping of mappings) {
        const value = extractFieldFromUrl(url, mapping.url_patterns)
        if (value) {
          extractedFields[mapping.field_name] = value
          console.log(`  ✓ Extracted ${mapping.display_name}: ${value}`)

          // Track the primary field (usually supplier_part_number)
          if (mapping.required_for_enrichment && !primaryFieldValue) {
            primaryFieldValue = value
            primaryFieldName = mapping.field_name
          }
        } else {
          console.log(`  ✗ Could not extract ${mapping.display_name} from URL`)
        }
      }

      if (!primaryFieldValue) {
        console.warn('Could not extract required field from URL')
        toast.error(`Could not extract part number from ${formattedName} URL`)
        return
      }

      console.log(`🔄 Auto-enriching ${formattedName} part: ${primaryFieldValue}`)
      toast.loading(`Fetching part details from ${formattedName}...`, { duration: 2000 })

      // Step 3: Auto-populate extracted fields
      setFormData((prev) => ({
        ...prev,
        ...extractedFields,
      }))

      // Step 4: Call unified backend enrichment endpoint
      // This uses SupplierDataMapper on backend for consistent data mapping
      const enrichedData = await partsService.enrichFromSupplier(
        supplierName,
        primaryFieldValue // Can be URL, part number, or MPN - backend will handle extraction
      )

      if (!enrichedData) {
        console.warn('No enriched data returned from backend')
        toast.error(`Could not fetch details for ${primaryFieldValue} from ${formattedName}`)
        return
      }

      console.log('✅ Enriched data from backend (via SupplierDataMapper):', enrichedData)

      // Step 5: Auto-populate enriched fields
      // The backend already mapped everything via SupplierDataMapper, so just use it directly
      setFormData((prev) => ({
        ...prev,
        name: enrichedData.part_name || prev.name,
        part_number:
          enrichedData.supplier_part_number || enrichedData.part_number || prev.part_number,
        supplier_part_number: enrichedData.supplier_part_number || prev.supplier_part_number,
        manufacturer: enrichedData.manufacturer || prev.manufacturer,
        manufacturer_part_number:
          enrichedData.manufacturer_part_number || prev.manufacturer_part_number,
        description: enrichedData.description || prev.description,
        unit_price: enrichedData.unit_price || prev.unit_price,
        currency: enrichedData.currency || prev.currency,
        // Preserve product_url from earlier URL paste (it's already in prev from handleSupplierUrlChange)
        product_url: prev.product_url,
      }))

      // Set image if available
      if (enrichedData.image_url) {
        setImageUrl(enrichedData.image_url)
      }

      // Populate custom properties from additional_properties (already mapped by backend)
      if (
        enrichedData.additional_properties &&
        Object.keys(enrichedData.additional_properties).length > 0
      ) {
        const customProps = Object.entries(enrichedData.additional_properties)
          .filter(([key]) => !['last_enrichment_date', 'enrichment_source'].includes(key)) // Filter out metadata
          .map(([key, value]) => ({
            key,
            value: String(value),
          }))
        setCustomProperties(customProps)
        console.log('✅ Populated custom properties from backend:', customProps)
      }

      // Auto-select "Hardware" category for Bolt Depot parts
      if (supplierName.toLowerCase() === 'boltdepot') {
        const hardwareCategory = categories.find(cat => cat.name.toLowerCase() === 'hardware')
        if (hardwareCategory && !selectedCategories.includes(hardwareCategory.id)) {
          setSelectedCategories([...selectedCategories, hardwareCategory.id])
          console.log('✅ Auto-selected Hardware category for Bolt Depot part')
        } else if (!hardwareCategory) {
          // Hardware category doesn't exist yet, it will be auto-created on backend
          console.log('ℹ️ Hardware category will be auto-created when part is saved')
        }
      }

      toast.success(`Auto-populated from ${formattedName}!`)
    } catch (error) {
      console.error('Error during dynamic auto-enrichment:', error)
      // Check if this is a credentials error
      const err = error as { response?: { status?: number }; message?: string }
      if (err.response?.status === 401 || err.response?.status === 403) {
        console.warn('Supplier credentials not configured or invalid')
        toast.error(`${formattedName} needs to be configured with valid credentials`)
      } else {
        console.warn('Failed to auto-enrich:', err.message || error)
        // Silent failure for other errors - user can manually enter details
      }
    }
  }

  const createSimpleSupplier = async (supplierName: string, formattedName: string, url: string) => {
    try {
      // Check if supplier already exists
      const existingSuppliers = await supplierService.getSuppliers()
      const supplierExists = existingSuppliers.some(
        (s) => s.supplier_name.toLowerCase() === supplierName.toLowerCase()
      )

      if (!supplierExists) {
        // Create simple supplier config with website URL (triggers favicon fetch on backend)
        const supplierConfig = {
          supplier_name: supplierName.toLowerCase(),
          display_name: formattedName,
          description: `Auto-detected supplier: ${formattedName}`,
          website_url: url.startsWith('http') ? url : `https://${url}`,
          supplier_type: 'simple' as const,
          api_type: 'rest' as const,
          base_url: '',
          enabled: true,
          supports_datasheet: false,
          supports_image: false,
          supports_pricing: false,
          supports_stock: false,
          supports_specifications: false,
        }

        await supplierService.createSupplier(supplierConfig)
        console.log(
          `Created simple supplier config for ${formattedName} - favicon will be fetched automatically`
        )
      }
    } catch (error) {
      // Silent failure - supplier config creation is optional, part creation will still work
      console.warn('Failed to create supplier config for favicon:', error)
    }
  }

  const handleConfigureSupplier = () => {
    // Close current modal and navigate to supplier configuration
    setShowConfigureSupplierPrompt(false)
    toast.info(
      `Please configure ${detectedSupplierInfo?.name} in the Suppliers page to enable enrichment`
    )
    // TODO: Could open supplier configuration modal directly here
  }

  const handleAddAsSimpleSupplier = async () => {
    if (detectedSupplierInfo) {
      const supplierName = detectedSupplierInfo.name.toLowerCase()
      await createSimpleSupplier(supplierName, detectedSupplierInfo.name, detectedSupplierInfo.url)
      setShowConfigureSupplierPrompt(false)
      setDetectedSupplierInfo(null)
    }
  }

  const handleCategoryCreated = async () => {
    // Reload categories and auto-select the new one
    try {
      const categoriesData = await categoriesService.getAllCategories()
      setCategories(categoriesData || [])

      // Find the newest category (assuming it's the last one after sort)
      if (categoriesData && categoriesData.length > 0) {
        const sortedCategories = categoriesData.sort(
          (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestCategory = sortedCategories[0]
        if (!selectedCategories.includes(newestCategory.id)) {
          setSelectedCategories([...selectedCategories, newestCategory.id])
        }
      }
    } catch (error) {
      console.error('Failed to reload categories:', error)
    }
    setShowAddCategoryModal(false)
  }

  const handleLocationCreated = async () => {
    // Reload locations and auto-select the new one
    try {
      const locationsData = await locationsService.getAllLocations()
      setLocations(locationsData || [])

      // Find the newest location
      if (locationsData && locationsData.length > 0) {
        const sortedLocations = locationsData.sort(
          (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestLocation = sortedLocations[0]
        setFormData({ ...formData, location_id: newestLocation.id })
      }
    } catch (error) {
      console.error('Failed to reload locations:', error)
    }
    setShowAddLocationModal(false)
  }

  const handleProjectCreated = async () => {
    // Reload projects and auto-select the new one
    try {
      const projectsData = await projectsService.getAllProjects()
      setProjects(projectsData || [])

      // Find the newest project
      if (projectsData && projectsData.length > 0) {
        const sortedProjects = projectsData.sort(
          (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestProject = sortedProjects[0]
        if (!selectedProjects.includes(newestProject.id)) {
          setSelectedProjects([...selectedProjects, newestProject.id])
        }
      }
    } catch (error) {
      console.error('Failed to reload projects:', error)
    }
    setShowAddProjectModal(false)
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Add New Part" size="xl">
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Row 1: Basic Info - 3 columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Part Name" required error={errors.name}>
              <input
                type="text"
                className="input w-full focus:ring-primary/50 focus:border-primary"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter part name"
              />
            </FormField>

            <FormField label="Part Number" error={errors.part_number}>
              <input
                type="text"
                className="input w-full focus:ring-primary/50 focus:border-primary"
                value={formData.part_number}
                onChange={(e) => setFormData({ ...formData, part_number: e.target.value })}
                placeholder="Enter part number"
              />
            </FormField>

            <FormField
              label="Supplier"
              error={errors.supplier}
              description="Select or enter supplier"
            >
              <SupplierSelector
                value={formData.supplier}
                onChange={(value) => setFormData({ ...formData, supplier: value })}
                error={errors.supplier}
                placeholder="Select supplier..."
              />
            </FormField>
          </div>

          {/* Row 2: Description and Supplier URL - 2 columns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Description" error={errors.description}>
              <textarea
                className="input w-full min-h-[80px] resize-y focus:ring-primary/50 focus:border-primary"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter part description (optional)"
                rows={2}
              />
            </FormField>

            <FormField
              label="Supplier URL"
              error={errors.supplier_url}
              description="Paste product URL for auto-detection"
            >
              <input
                type="url"
                className="input w-full focus:ring-primary/50 focus:border-primary"
                value={formData.supplier_url}
                onChange={(e) => handleSupplierUrlChange(e.target.value)}
                placeholder="https://ebay.com/itm/12345..."
              />
            </FormField>
          </div>

          {/* Row 3: Quantities, Emoji, and Location - 4 columns */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <div className="space-y-4">
              <FormField label="Quantity" required error={errors.quantity}>
                <input
                  type="number"
                  min="0"
                  className="input w-full focus:ring-primary/50 focus:border-primary"
                  value={formData.quantity === 0 ? '' : formData.quantity}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      quantity: e.target.value === '' ? 0 : parseInt(e.target.value),
                    })
                  }
                  placeholder="0"
                />
              </FormField>

              <FormField
                label="Emoji Icon"
                description="For printer labels"
              >
                <EmojiPicker
                  value={emoji || undefined}
                  onChange={(selectedEmoji) => setEmoji(selectedEmoji)}
                  placeholder="Select emoji..."
                />
              </FormField>
            </div>

            <FormField
              label={
                <div className="flex items-center gap-1">
                  <span>Min. Quantity</span>
                  <TooltipIcon
                    variant="help"
                    position="top"
                    tooltip="Alert when quantity falls below this threshold"
                  />
                </div>
              }
              error={errors.minimum_quantity}
            >
              <input
                type="number"
                min="0"
                className="input w-full focus:ring-primary/50 focus:border-primary"
                value={formData.minimum_quantity === 0 ? '' : formData.minimum_quantity}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    minimum_quantity: e.target.value === '' ? 0 : parseInt(e.target.value),
                  })
                }
                placeholder="0"
              />
            </FormField>

            <div className="md:col-span-2 space-y-2">
              <label className="text-sm font-medium text-primary">Location</label>
              <div className="relative">
                <LocationTreeSelector
                  selectedLocationId={formData.location_id}
                  onLocationSelect={(locationId) =>
                    setFormData({ ...formData, location_id: locationId || '' })
                  }
                  description="Storage location"
                  error={errors.location_id}
                  showAddButton={false}
                  compact={true}
                  showLabel={false}
                />
                <button
                  type="button"
                  onClick={() => setShowAddLocationModal(true)}
                  className="absolute top-2 right-2 p-1.5 rounded-md bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/30"
                  disabled={loading}
                  title="Add new location"
                >
                  <Plus className="w-4 h-4 text-primary" />
                </button>
              </div>
            </div>
          </div>

          {/* Supplier-Specific Required Fields */}
          {loadingSupplierFields && (
            <div className="p-3 bg-theme-secondary rounded-md">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <p className="text-sm text-theme-secondary">Loading supplier requirements...</p>
              </div>
            </div>
          )}

          {!loadingSupplierFields && supplierRequiredFields.length > 0 && (
            <div className="space-y-3 p-3 bg-theme-secondary rounded-md border border-theme-primary">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold text-theme-primary">
                  Required for Enrichment from {formData.supplier}
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {supplierRequiredFields.map((field) => (
                  <FormField
                    key={field.field}
                    label={field.label}
                    required
                    error={errors[field.field]}
                    description={field.help_text || field.description}
                  >
                    <input
                      type={field.type}
                      className="input w-full"
                      value={
                        (formData as Record<string, unknown>)[field.field]?.toString() || ''
                      }
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          [field.field]: e.target.value,
                        })
                      }
                      placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                    />
                  </FormField>
                ))}
              </div>
            </div>
          )}

          {/* Row 4: Image and Categories/Projects - larger image */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
            <FormField label="Part Image">
              <ImageUpload
                onImageUploaded={setImageUrl}
                currentImageUrl={imageUrl}
                placeholder="Upload image"
                className="w-full"
              />
            </FormField>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-primary">Categories</label>
                <CustomSelect
                  value=""
                  onChange={() => {}}
                  multiSelect={true}
                  selectedValues={selectedCategories}
                  onMultiSelectChange={(values) => setSelectedCategories(values)}
                  options={categories.map((cat) => ({
                    value: cat.id,
                    label: cat.name,
                  }))}
                  placeholder="Select categories..."
                  searchable={true}
                  searchPlaceholder="Search..."
                  error={errors.categories}
                  onAddNew={() => setShowAddCategoryModal(true)}
                  addNewLabel="Add Category"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-primary">Projects</label>
                <CustomSelect
                  value=""
                  onChange={() => {}}
                  multiSelect={true}
                  selectedValues={selectedProjects}
                  onMultiSelectChange={(values) => setSelectedProjects(values)}
                  options={projects.map((proj) => ({
                    value: proj.id,
                    label: proj.name,
                  }))}
                  placeholder="Select projects..."
                  searchable={true}
                  searchPlaceholder="Search..."
                  error={errors.projects}
                  onAddNew={() => setShowAddProjectModal(true)}
                  addNewLabel="Add Project"
                />
              </div>
            </div>
          </div>

          {/* Additional Properties - Collapsible */}
          <details className="group" open={isAdditionalPropsOpen}>
            <summary className="flex items-center justify-between cursor-pointer p-3 bg-primary/5 border border-primary/20 rounded-md hover:bg-primary/10 transition-colors list-none">
              <div className="flex items-center gap-2">
                <ChevronDown className="w-4 h-4 text-primary transition-transform group-open:rotate-180" />
                <label className="text-sm font-medium text-primary">Additional Properties</label>
                <TooltipIcon
                  variant="help"
                  position="left"
                  tooltip={
                    <div className="space-y-2">
                      <p className="font-semibold">What are Additional Properties?</p>
                      <p>
                        Add any additional information specific to this part that doesn't fit in the
                        standard fields.
                      </p>
                      <div className="pt-2 border-t border-white/20">
                        <p className="font-semibold mb-1">Examples:</p>
                        <ul className="text-xs space-y-1 ml-4 list-disc">
                          <li>
                            <span className="font-medium">Tolerance:</span> ±5%
                          </li>
                          <li>
                            <span className="font-medium">Operating Temp:</span> -40°C to 85°C
                          </li>
                          <li>
                            <span className="font-medium">Package Type:</span> SMD 0805
                          </li>
                        </ul>
                      </div>
                    </div>
                  }
                />
                <span className="text-xs text-theme-muted">
                  ({customProperties.length} {customProperties.length === 1 ? 'property' : 'properties'})
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault()
                    addCustomProperty()
                  }}
                  className="px-2 py-1 rounded-md bg-primary/10 hover:bg-primary/20 transition-colors border border-primary/30 flex items-center gap-1 text-xs text-primary font-medium"
                >
                  <Plus className="w-3 h-3" />
                  Add
                </button>
              </div>
            </summary>

            <div className="mt-3 space-y-2">
              {customProperties.map((prop, index) => (
                <div key={index} className="grid grid-cols-[1fr,1fr,auto] gap-2">
                  <input
                    type="text"
                    placeholder="Property name"
                    className="input w-full"
                    value={prop.key}
                    onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Property value"
                    className="input w-full"
                    value={prop.value}
                    onChange={(e) => updateCustomProperty(index, 'value', e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => removeCustomProperty(index)}
                    className="btn btn-secondary btn-sm"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {customProperties.length === 0 && (
                <p className="text-xs text-theme-muted p-2">
                  No custom properties added. Click "Add" to include additional specifications.
                </p>
              )}
            </div>
          </details>

          {/* Actions */}
          <div className="flex justify-between items-center pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => {
                clearFormData()
                toast.success('Form cleared')
              }}
              className="btn btn-ghost text-xs"
              disabled={loading}
            >
              Clear Form
            </button>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="btn btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary flex items-center gap-2"
                disabled={loading}
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {loading ? 'Creating...' : 'Create Part'}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Inline Modals */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryCreated}
        existingCategories={categories.map((c) => c.name)}
      />

      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationCreated}
      />

      <AddProjectModal
        isOpen={showAddProjectModal}
        onClose={() => setShowAddProjectModal(false)}
        onSuccess={handleProjectCreated}
        existingProjects={projects.map((p) => p.name)}
      />

      {/* Supplier Configuration Prompt */}
      <Modal
        isOpen={showConfigureSupplierPrompt}
        onClose={() => {
          setShowConfigureSupplierPrompt(false)
          setDetectedSupplierInfo(null)
        }}
        title="Supplier Supports Enrichment"
        size="md"
      >
        <div className="space-y-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-primary">
              <strong className="font-semibold">{detectedSupplierInfo?.name}</strong> is available
              in the supplier registry and supports automatic part enrichment!
            </p>
          </div>

          <div className="space-y-3">
            <p className="text-sm text-primary">You have two options:</p>

            <div className="space-y-2">
              <div className="border border-theme-primary rounded-lg p-3 bg-theme-secondary">
                <p className="font-medium text-sm text-primary mb-1">
                  ✨ Configure for Enrichment (Recommended)
                </p>
                <p className="text-xs text-theme-muted">
                  Set up API credentials to enable automatic fetching of datasheets, images,
                  specifications, pricing, and stock levels.
                </p>
              </div>

              <div className="border border-theme-primary rounded-lg p-3 bg-theme-secondary">
                <p className="font-medium text-sm text-primary mb-1">📎 Add as Simple Supplier</p>
                <p className="text-xs text-theme-muted">
                  Just save the URL and favicon - no automatic enrichment features.
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <button type="button" onClick={handleAddAsSimpleSupplier} className="btn btn-secondary">
              Add as Simple Supplier
            </button>
            <button type="button" onClick={handleConfigureSupplier} className="btn btn-primary">
              Configure for Enrichment
            </button>
          </div>
        </div>
      </Modal>
    </Modal>
  )
}

export default AddPartModal
