import { useState, useEffect } from 'react'
import { Save, Package, Plus, X, Upload, Image, Tag, MapPin } from 'lucide-react'
import Modal from '@/components/ui/Modal'
import FormField from '@/components/ui/FormField'
import ImageUpload from '@/components/ui/ImageUpload'
import { CustomSelect } from '@/components/ui/CustomSelect'
import LocationTreeSelector from '@/components/ui/LocationTreeSelector'
import SupplierSelector from '@/components/ui/SupplierSelector'
import { TooltipIcon } from '@/components/ui/Tooltip'
import AddCategoryModal from '@/components/categories/AddCategoryModal'
import AddLocationModal from '@/components/locations/AddLocationModal'
import { partsService } from '@/services/parts.service'
import { locationsService } from '@/services/locations.service'
import { categoriesService } from '@/services/categories.service'
import { utilityService } from '@/services/utility.service'
import { tasksService } from '@/services/tasks.service'
import supplierService from '@/services/supplier.service'
import { dynamicSupplierService } from '@/services/dynamic-supplier.service'
import { CreatePartRequest } from '@/types/parts'
import { Location, Category } from '@/types/parts'
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
    supplier_part_number: '',
    location_id: '',
    categories: [],
    additional_properties: {}
  })

  const [locations, setLocations] = useState<Location[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [customProperties, setCustomProperties] = useState<Array<{key: string, value: string}>>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>('')

  // Supplier required fields for enrichment
  const [supplierRequiredFields, setSupplierRequiredFields] = useState<CredentialFieldDefinition[]>([])
  const [loadingSupplierFields, setLoadingSupplierFields] = useState(false)
  const [configuredSuppliers, setConfiguredSuppliers] = useState<string[]>([])
  const [availableSuppliers, setAvailableSuppliers] = useState<string[]>([]) // Suppliers in registry

  // Smart supplier detection state
  const [showConfigureSupplierPrompt, setShowConfigureSupplierPrompt] = useState(false)
  const [detectedSupplierInfo, setDetectedSupplierInfo] = useState<{name: string, url: string} | null>(null)

  // Inline modal states
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false)
  const [showAddLocationModal, setShowAddLocationModal] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadData()
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
      const [locationsData, categoriesData, suppliersData, availableSuppliersData] = await Promise.all([
        locationsService.getAllLocations(),
        categoriesService.getAllCategories(),
        supplierService.getSuppliers(true), // Get only enabled/configured suppliers
        dynamicSupplierService.getAvailableSuppliers() // Get all available suppliers from registry
      ])
      setLocations(locationsData || [])
      setCategories(categoriesData || [])

      // Store configured supplier names for checking against custom suppliers
      const configuredNames = suppliersData.map(s => s.supplier_name.toLowerCase())
      setConfiguredSuppliers(configuredNames)

      // Store available suppliers from registry - these are already lowercase strings
      const availableNames = Array.isArray(availableSuppliersData)
        ? availableSuppliersData.map(s => s.toLowerCase())
        : []
      setAvailableSuppliers(availableNames)

      console.log('🔍 Smart Supplier Detection Setup:')
      console.log('  Configured suppliers:', configuredNames)
      console.log('  Available suppliers from registry:', availableNames)
    } catch (error) {
      console.error('Failed to load data:', error)
      toast.error('Failed to load data')
      // Set empty arrays as fallbacks
      setLocations([])
      setCategories([])
      setConfiguredSuppliers([])
      setAvailableSuppliers([])
    } finally {
      setLoadingData(false)
    }
  }

  const loadSupplierRequiredFields = async (supplierName: string) => {
    try {
      setLoadingSupplierFields(true)
      // Get enrichment requirements for the supplier
      const response = await partsService.getSupplierEnrichmentRequirements(supplierName)

      console.log('Enrichment requirements response:', response)

      // Check if response and required_fields exist
      if (!response || !response.required_fields) {
        console.warn('No required fields in response:', response)
        setSupplierRequiredFields([])
        return
      }

      // Convert enrichment requirements to field definitions format
      const requiredFields = response.required_fields.map((field: any) => ({
        field: field.field_name,
        label: field.display_name,
        type: 'text', // Enrichment fields are typically text inputs
        required: true,
        description: field.description,
        placeholder: field.example ? `e.g., ${field.example}` : `Enter ${field.display_name.toLowerCase()}`,
        help_text: field.description,
        validation: field.validation_pattern ? { pattern: field.validation_pattern } : undefined
      }))

      console.log('Converted required fields:', requiredFields)
      setSupplierRequiredFields(requiredFields)
    } catch (error) {
      console.error('Failed to load supplier required fields:', error)
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
    supplierRequiredFields.forEach(field => {
      const fieldName = field.field as keyof CreatePartRequest
      const value = formData[fieldName] as string
      if (!value || (typeof value === 'string' && !value.trim())) {
        newErrors[field.field] = `${field.label} is required for enrichment from ${formData.supplier}`
      }

      // Additional pattern validation if specified
      if (value && field.validation?.pattern) {
        const pattern = new RegExp(field.validation.pattern)
        if (!pattern.test(value)) {
          newErrors[field.field] = `${field.label} format is invalid (expected format like: ${field.placeholder || field.label})`
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
      const properties: Record<string, any> = {}
      customProperties.forEach(({ key, value }) => {
        if (key.trim() && value.trim()) {
          properties[key.trim()] = value.trim()
        }
      })

      // Convert category IDs to category names
      const categoryNames = selectedCategories.map(categoryId => {
        const category = categories.find(cat => cat.id === categoryId)
        return category?.name
      }).filter(Boolean) as string[]

      const submitData: CreatePartRequest = {
        ...formData,
        image_url: imageUrl || undefined,
        categories: categoryNames,
        additional_properties: Object.keys(properties).length > 0 ? properties : undefined
      }

      console.log('🚀 Creating part with data:', submitData)
      const createdPart = await partsService.createPart(submitData)
      toast.success('Part created successfully')

      // Auto-enrich only if supplier is configured and supports enrichment
      if (formData.supplier && formData.supplier.trim()) {
        // Check if supplier is in the configured suppliers list (has API capabilities)
        const isConfiguredSupplier = configuredSuppliers.includes(formData.supplier.toLowerCase())

        if (isConfiguredSupplier) {
          try {
            console.log(`Auto-enriching part ${createdPart.id} with supplier ${formData.supplier}`)
            const enrichmentTask = await tasksService.createPartEnrichmentTask({
              part_id: createdPart.id,
              supplier: formData.supplier.trim(),
              capabilities: ['get_part_details', 'fetch_datasheet', 'fetch_pricing_stock'],
              force_refresh: false
            })
            toast.success(`Enrichment task created: ${enrichmentTask.data.name}`)
            console.log('Enrichment task created:', enrichmentTask.data)
          } catch (error) {
            console.error('Failed to create enrichment task:', error)
            toast.error('Part created but enrichment failed to start')
          }
        } else {
          console.log(`Supplier "${formData.supplier}" is not configured for enrichment - skipping auto-enrich`)
        }
      }
      
      console.log('Part created successfully, calling onSuccess and handleClose')
      onSuccess()
      handleClose()
    } catch (error: any) {
      console.error('Failed to create part:', error)
      console.error('Error response:', error.response?.data)
      console.error('Error status:', error.response?.status)
      
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message || 
                          'Failed to create part'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
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
      additional_properties: {}
    })
    setSelectedCategories([])
    setCustomProperties([])
    setErrors({})
    setImageUrl('')
    setSupplierRequiredFields([])

    // Close any open inline modals
    setShowAddCategoryModal(false)
    setShowAddLocationModal(false)

    onClose()
  }

  const addCustomProperty = () => {
    setCustomProperties([...customProperties, { key: '', value: '' }])
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
      // Check if input looks like a URL
      const urlPattern = /^https?:\/\//i;
      if (!urlPattern.test(url)) {
        return null;
      }

      const urlObj = new URL(url);
      const hostname = urlObj.hostname;

      // Remove www. prefix if present
      const domain = hostname.replace(/^www\./, '');

      // Extract base domain name (e.g., "ebay" from "ebay.com")
      const parts = domain.split('.');
      if (parts.length >= 2) {
        return parts[0]; // Return first part (e.g., "ebay")
      }

      return domain;
    } catch (err) {
      return null;
    }
  };

  const handleSupplierUrlChange = async (url: string) => {
    setFormData({ ...formData, supplier_url: url });

    // If supplier field is empty and URL contains a domain, auto-populate supplier
    if (!formData.supplier && url.trim()) {
      const supplierName = extractDomainFromUrl(url);
      if (supplierName) {
        // Capitalize first letter
        const formattedName = supplierName.charAt(0).toUpperCase() + supplierName.slice(1);
        setFormData({ ...formData, supplier_url: url, supplier: formattedName });
        toast.success(`Auto-detected supplier: ${formattedName}`);

        // Check if supplier is available in registry but not configured
        const isAvailable = availableSuppliers.includes(supplierName.toLowerCase());
        const isConfigured = configuredSuppliers.includes(supplierName.toLowerCase());

        console.log('🔍 Smart Supplier Detection Check:')
        console.log('  Detected supplier:', supplierName.toLowerCase())
        console.log('  Is available in registry?', isAvailable)
        console.log('  Is configured?', isConfigured)
        console.log('  Available suppliers:', availableSuppliers)
        console.log('  Configured suppliers:', configuredSuppliers)

        if (isAvailable && !isConfigured) {
          // Supplier supports enrichment but needs configuration
          console.log('✨ Showing configuration prompt for', formattedName)
          setDetectedSupplierInfo({ name: formattedName, url });
          setShowConfigureSupplierPrompt(true);
          return; // Don't create simple supplier yet - wait for user choice
        }

        // If supplier is not available in registry, create as simple supplier
        if (!isAvailable) {
          console.log('📎 Creating simple supplier for', formattedName)
          await createSimpleSupplier(supplierName, formattedName, url);
        } else if (isConfigured) {
          console.log('✅ Supplier is already configured - attempting auto-enrichment')
          // Supplier is configured - try to auto-enrich from URL
          await attemptAutoEnrichment(url, supplierName, formattedName);
        }
      }
    }
  };

  const attemptAutoEnrichment = async (url: string, supplierName: string, formattedName: string) => {
    try {
      // Extract product/part number from URL
      const productId = extractProductIdFromUrl(url);
      if (!productId) {
        console.log('Could not extract product ID from URL');
        return;
      }

      console.log(`🔄 Auto-enriching from ${formattedName} product ID: ${productId}`);
      toast.loading(`Fetching part details from ${formattedName}...`, { duration: 2000 });

      // Call the supplier API using the service method with empty credentials
      // The backend should use stored credentials for configured suppliers
      const partDetails = await dynamicSupplierService.getPartDetails(
        supplierName.toLowerCase(),
        productId,
        {}, // Empty credentials - backend will use stored credentials
        {}  // Empty config - backend will use stored config
      );

      if (!partDetails) {
        console.warn('No part details returned');
        return;
      }

      console.log('✅ Auto-enriched part details:', partDetails);

      // Auto-populate form fields
      setFormData(prev => ({
        ...prev,
        name: partDetails.description || partDetails.part_name || prev.name,
        part_number: partDetails.supplier_part_number || productId || prev.part_number,
        supplier_part_number: partDetails.supplier_part_number || productId || prev.supplier_part_number,
        description: partDetails.description || prev.description,
      }));

      // Set image if available
      if (partDetails.image_url) {
        setImageUrl(partDetails.image_url);
      }

      toast.success(`Auto-populated from ${formattedName}!`);
    } catch (error: any) {
      console.error('Error during auto-enrichment:', error);
      // Check if this is a credentials error
      if (error.response?.status === 401 || error.response?.status === 403) {
        console.warn('Supplier credentials not configured or invalid');
        toast.error(`${formattedName} needs to be configured with valid credentials`);
      }
      // Silent failure for other errors - user can manually enter details
    }
  };

  const extractProductIdFromUrl = (url: string): string | null => {
    try {
      // Common patterns for different suppliers
      const patterns = [
        /\/product\/(\d+)/i,           // Adafruit: /product/4759
        /\/products\/(.+?)(?:\/|$)/i,  // Generic: /products/ABC123
        /\/item\/(.+?)(?:\/|$)/i,      // Generic: /item/ABC123
        /\/p\/(.+?)(?:\/|$)/i,         // Short: /p/ABC123
      ];

      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
          return match[1];
        }
      }

      return null;
    } catch {
      return null;
    }
  };

  const createSimpleSupplier = async (supplierName: string, formattedName: string, url: string) => {
    try {
      // Check if supplier already exists
      const existingSuppliers = await supplierService.getSuppliers();
      const supplierExists = existingSuppliers.some(
        s => s.supplier_name.toLowerCase() === supplierName.toLowerCase()
      );

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
          supports_specifications: false
        };

        await supplierService.createSupplier(supplierConfig);
        console.log(`Created simple supplier config for ${formattedName} - favicon will be fetched automatically`);
      }
    } catch (error) {
      // Silent failure - supplier config creation is optional, part creation will still work
      console.warn('Failed to create supplier config for favicon:', error);
    }
  };

  const handleConfigureSupplier = () => {
    // Close current modal and navigate to supplier configuration
    setShowConfigureSupplierPrompt(false);
    toast.info(`Please configure ${detectedSupplierInfo?.name} in the Suppliers page to enable enrichment`);
    // TODO: Could open supplier configuration modal directly here
  };

  const handleAddAsSimpleSupplier = async () => {
    if (detectedSupplierInfo) {
      const supplierName = detectedSupplierInfo.name.toLowerCase();
      await createSimpleSupplier(supplierName, detectedSupplierInfo.name, detectedSupplierInfo.url);
      setShowConfigureSupplierPrompt(false);
      setDetectedSupplierInfo(null);
    }
  };

  const handleCategoryCreated = async () => {
    // Reload categories and auto-select the new one
    try {
      const categoriesData = await categoriesService.getAllCategories()
      setCategories(categoriesData || [])
      
      // Find the newest category (assuming it's the last one after sort)
      if (categoriesData && categoriesData.length > 0) {
        const sortedCategories = categoriesData.sort((a, b) => 
          new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
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
        const sortedLocations = locationsData.sort((a, b) => 
          new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        )
        const newestLocation = sortedLocations[0]
        setFormData({ ...formData, location_id: newestLocation.id })
      }
    } catch (error) {
      console.error('Failed to reload locations:', error)
    }
    setShowAddLocationModal(false)
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add New Part" size="xl">
      {loadingData ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-secondary mt-2">Loading...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Basic Information */}
            <FormField label="Part Name" required error={errors.name}>
              <input
                type="text"
                className="input w-full"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter part name"
              />
            </FormField>

            <FormField label="Part Number" error={errors.part_number}>
              <input
                type="text"
                className="input w-full"
                value={formData.part_number}
                onChange={(e) => setFormData({ ...formData, part_number: e.target.value })}
                placeholder="Enter part number"
              />
            </FormField>
          </div>

          {/* Description Field - Full Width */}
          <FormField label="Description" error={errors.description}>
            <textarea
              className="input w-full min-h-[100px] resize-y"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Enter part description (optional)"
              rows={3}
            />
          </FormField>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            <FormField label="Quantity" required error={errors.quantity}>
              <input
                type="number"
                min="0"
                className="input w-full"
                value={formData.quantity === 0 ? '' : formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: e.target.value === '' ? 0 : parseInt(e.target.value) })}
                placeholder="0"
              />
            </FormField>

            <FormField label="Minimum Quantity" error={errors.minimum_quantity} description="Alert when quantity falls below this level">
              <input
                type="number"
                min="0"
                className="input w-full"
                value={formData.minimum_quantity === 0 ? '' : formData.minimum_quantity}
                onChange={(e) => setFormData({ ...formData, minimum_quantity: e.target.value === '' ? 0 : parseInt(e.target.value) })}
                placeholder="0"
              />
            </FormField>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-primary">Location</label>
                <button
                  type="button"
                  onClick={() => setShowAddLocationModal(true)}
                  className="btn btn-secondary btn-sm flex items-center gap-1 text-xs"
                  disabled={loading}
                >
                  <MapPin className="w-3 h-3" />
                  Add Location
                </button>
              </div>
              <LocationTreeSelector
                selectedLocationId={formData.location_id}
                onLocationSelect={(locationId) => setFormData({ ...formData, location_id: locationId || '' })}
                description="Select where this part will be stored"
                error={errors.location_id}
                showAddButton={false}
                compact={true}
                showLabel={false}
              />
            </div>

            <FormField
              label="Supplier"
              error={errors.supplier}
              description="Select a configured supplier or enter a custom one"
            >
              <SupplierSelector
                value={formData.supplier}
                onChange={(value) => setFormData({ ...formData, supplier: value })}
                error={errors.supplier}
                placeholder="Select supplier..."
              />
            </FormField>
          </div>

          <FormField
            label="Supplier URL"
            error={errors.supplier_url}
            description="Paste product URL - supplier will be auto-detected if not set"
          >
            <input
              type="url"
              className="input w-full"
              value={formData.supplier_url}
              onChange={(e) => handleSupplierUrlChange(e.target.value)}
              placeholder="https://ebay.com/itm/12345... (auto-detects supplier)"
            />
          </FormField>

          {/* Supplier-Specific Required Fields */}
          {loadingSupplierFields && (
            <div className="p-4 bg-theme-secondary rounded-md">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <p className="text-sm text-theme-secondary">Loading supplier requirements...</p>
              </div>
            </div>
          )}

          {!loadingSupplierFields && supplierRequiredFields.length > 0 && (
            <div className="space-y-4 p-4 bg-theme-secondary rounded-md border border-theme-primary">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold text-theme-primary">
                  Required for Enrichment from {formData.supplier}
                </h3>
              </div>
              <p className="text-xs text-theme-muted">
                These fields are required to enable automatic part data enrichment from {formData.supplier}.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                      value={(formData as any)[field.field] || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        [field.field]: e.target.value
                      })}
                      placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                    />
                  </FormField>
                ))}
              </div>
            </div>
          )}

          {/* Image Upload */}
          <FormField label="Part Image" description="Upload, drag & drop, or paste an image of the part (max 5MB)">
            <ImageUpload
              onImageUploaded={setImageUrl}
              currentImageUrl={imageUrl}
              placeholder="Upload part image"
              className="w-full"
            />
          </FormField>

          {/* Categories */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-primary">Categories</label>
              <button
                type="button"
                onClick={() => setShowAddCategoryModal(true)}
                className="btn btn-secondary btn-sm flex items-center gap-1 text-xs"
                disabled={loading}
              >
                <Tag className="w-3 h-3" />
                Add Category
              </button>
            </div>
            <CustomSelect
              value=""
              onChange={() => {}} // Not used in multi-select mode
              multiSelect={true}
              selectedValues={selectedCategories}
              onMultiSelectChange={(values) => setSelectedCategories(values)}
              options={categories.map(cat => ({
                value: cat.id,
                label: cat.name
              }))}
              placeholder="Select categories..."
              searchable={true}
              searchPlaceholder="Search categories..."
              error={errors.categories}
            />
            <p className="text-xs text-theme-muted">
              Select categories that apply to this part
            </p>
          </div>

          {/* Custom Properties */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-primary">Custom Properties</label>
                <TooltipIcon
                  variant="help"
                  position="left"
                  tooltip={
                    <div className="space-y-2">
                      <p className="font-semibold">What are Custom Properties?</p>
                      <p>Add any additional information specific to this part that doesn't fit in the standard fields.</p>
                      <div className="pt-2 border-t border-white/20">
                        <p className="font-semibold mb-1">Examples:</p>
                        <ul className="text-xs space-y-1 ml-4 list-disc">
                          <li><span className="font-medium">Tolerance:</span> ±5%</li>
                          <li><span className="font-medium">Operating Temp:</span> -40°C to 85°C</li>
                          <li><span className="font-medium">Package Type:</span> SMD 0805</li>
                          <li><span className="font-medium">Color:</span> Blue</li>
                          <li><span className="font-medium">Material:</span> ABS Plastic</li>
                        </ul>
                      </div>
                      <p className="text-xs pt-2 border-t border-white/20">
                        💡 Tip: These properties are searchable and can be used to filter parts later.
                      </p>
                    </div>
                  }
                />
              </div>
              <button
                type="button"
                onClick={addCustomProperty}
                className="btn btn-secondary btn-sm flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Add Property
              </button>
            </div>

            {customProperties.map((prop, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Property name (e.g., Tolerance)"
                  className="input flex-1"
                  value={prop.key}
                  onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Property value (e.g., ±5%)"
                  className="input flex-1"
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
              <p className="text-sm text-theme-secondary">
                No custom properties added. Click "Add Property" to include additional part specifications.
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
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
        </form>
      )}
      
      {/* Inline Modals */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryCreated}
        existingCategories={categories.map(c => c.name)}
      />

      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationCreated}
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
              <strong className="font-semibold">{detectedSupplierInfo?.name}</strong> is available in the supplier registry and supports automatic part enrichment!
            </p>
          </div>

          <div className="space-y-3">
            <p className="text-sm text-primary">
              You have two options:
            </p>

            <div className="space-y-2">
              <div className="border border-theme-primary rounded-lg p-3 bg-theme-secondary">
                <p className="font-medium text-sm text-primary mb-1">✨ Configure for Enrichment (Recommended)</p>
                <p className="text-xs text-theme-muted">
                  Set up API credentials to enable automatic fetching of datasheets, images, specifications, pricing, and stock levels.
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
            <button
              type="button"
              onClick={handleAddAsSimpleSupplier}
              className="btn btn-secondary"
            >
              Add as Simple Supplier
            </button>
            <button
              type="button"
              onClick={handleConfigureSupplier}
              className="btn btn-primary"
            >
              Configure for Enrichment
            </button>
          </div>
        </div>
      </Modal>
    </Modal>
  )
}

export default AddPartModal