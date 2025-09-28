import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Save, Trash2, Package, Plus, X, Info } from 'lucide-react';
import { partsService } from '../../services/parts.service';
import { locationsService } from '../../services/locations.service';
import { categoriesService } from '../../services/categories.service';
import { Part, CreatePartRequest } from '../../types/parts';
import { Location } from '../../types/locations';
import { Category } from '../../types/categories';
import FormField from '../../components/ui/FormField';
import ImageUpload from '../../components/ui/ImageUpload';
import AddCategoryModal from '../../components/categories/AddCategoryModal';
import AddLocationModal from '../../components/locations/AddLocationModal';
import CategorySelector from '../../components/ui/CategorySelector';
import LocationTreeSelector from '../../components/ui/LocationTreeSelector';
import toast from 'react-hot-toast';

const partSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  part_number: z.string().optional(),
  description: z.string().optional(),
  quantity: z.number().min(0, 'Quantity must be non-negative'),
  minimum_quantity: z.number().min(0, 'Minimum quantity must be non-negative').optional(),
  location_id: z.string().optional(),
  supplier: z.string().optional(),
  supplier_url: z.string().optional(),
  image_url: z.string().optional(),
  category_ids: z.array(z.string()).optional()
});

type PartFormData = z.infer<typeof partSchema>;

const EditPartPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [part, setPart] = useState<Part | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [additionalProperties, setAdditionalProperties] = useState<Record<string, any>>({});
  const [newPropertyKey, setNewPropertyKey] = useState('');
  const [newPropertyValue, setNewPropertyValue] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showAddCategoryModal, setShowAddCategoryModal] = useState(false);
  const [showAddLocationModal, setShowAddLocationModal] = useState(false);

  const buildLocationHierarchy = (locations: Location[]): Array<{id: string, name: string, level: number}> => {
    const result: Array<{id: string, name: string, level: number}> = []
    
    const addLocation = (location: Location, level: number = 0) => {
      result.push({
        id: location.id,
        name: location.name,
        level
      })
      
      // Find children in the flat list
      const children = locations.filter(loc => loc.parent_id === location.id)
      children
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(child => addLocation(child, level + 1))
    }
    
    // Start with root locations (no parent_id)
    const rootLocations = locations.filter(loc => !loc.parent_id)
    rootLocations
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach(location => addLocation(location))
    
    return result
  };

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
    setValue,
    watch,
    reset
  } = useForm<PartFormData>({
    resolver: zodResolver(partSchema),
    mode: 'onChange' // Enable validation on change
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        if (!id) return;
        
        const [partData, locationsData, categoriesData] = await Promise.all([
          partsService.getPart(id),
          locationsService.getAll(),
          categoriesService.getAll()
        ]);

        setPart(partData);
        setLocations(locationsData);
        setCategories(categoriesData);

        // Set additional properties
        setAdditionalProperties(partData.additional_properties || {});

        // Set selected categories
        const categoryIds = partData.categories?.map(cat => cat.id) || [];
        setSelectedCategories(categoryIds);

        // Populate form with existing data using reset() for proper form population
        reset({
          name: partData.name,
          part_number: partData.part_number || '',
          description: partData.description || '',
          quantity: partData.quantity,
          minimum_quantity: partData.minimum_quantity || 0,
          location_id: partData.location_id || undefined,
          supplier: partData.supplier || '',
          supplier_url: partData.supplier_url || '',
          image_url: partData.image_url || '',
          category_ids: categoryIds
        });
        
      } catch (error) {
        console.error('Error loading part data:', error);
        toast.error('Failed to load part data');
        navigate('/parts');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [id, reset, navigate]);

  const onSubmit = async (data: PartFormData) => {
    console.log('🚀 onSubmit called!');
    console.log('onSubmit data:', data);
    console.log('onSubmit context:', { id, part, selectedCategories });
    
    if (!id || !part) {
      console.error('Missing id or part:', { id, part });
      return;
    }
    
    setIsSaving(true);
    try {
      // Convert category IDs to category names
      const categoryNames = selectedCategories.map(categoryId => {
        const category = categories.find(cat => cat.id === categoryId)
        return category?.name
      }).filter(Boolean) as string[]

      console.log('Category conversion:', { selectedCategories, categoryNames });

      // Get the current image_url value from the form
      const currentImageUrl = watch('image_url');
      
      console.log('Image URL values:', { 
        dataImageUrl: data.image_url, 
        currentImageUrl, 
        watchedValue: watch('image_url') 
      });
      
      const updateData: CreatePartRequest = {
        ...data,
        image_url: currentImageUrl,
        categories: categoryNames,
        additional_properties: additionalProperties,
        // Convert empty strings to undefined to prevent foreign key constraint errors
        location_id: data.location_id === '' ? undefined : data.location_id,
        supplier_url: data.supplier_url === '' ? undefined : data.supplier_url
      };
      
      console.log('Sending update data:', updateData);
      
      await partsService.updatePart({ id, ...updateData });
      toast.success('Part updated successfully');
      navigate(`/parts/${id}`);
    } catch (error) {
      console.error('Error updating part:', error);
      toast.error('Failed to update part');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !part) return;
    
    if (!confirm(`Are you sure you want to delete "${part.name}"? This action cannot be undone.`)) {
      return;
    }
    
    setIsDeleting(true);
    try {
      await partsService.deletePart(id);
      toast.success('Part deleted successfully');
      navigate('/parts');
    } catch (error) {
      console.error('Error deleting part:', error);
      toast.error('Failed to delete part');
    } finally {
      setIsDeleting(false);
    }
  };

  const toggleCategory = (categoryId: string) => {
    const newSelected = selectedCategories.includes(categoryId)
      ? selectedCategories.filter(id => id !== categoryId)
      : [...selectedCategories, categoryId];
    
    console.log('Category toggled:', { categoryId, newSelected });
    setSelectedCategories(newSelected);
    setValue('category_ids', newSelected);
  };

  const addProperty = () => {
    if (newPropertyKey.trim() && newPropertyValue.trim()) {
      setAdditionalProperties(prev => ({
        ...prev,
        [newPropertyKey.trim()]: newPropertyValue.trim()
      }));
      setNewPropertyKey('');
      setNewPropertyValue('');
    }
  };

  const removeProperty = (key: string) => {
    setAdditionalProperties(prev => {
      const newProps = { ...prev };
      delete newProps[key];
      return newProps;
    });
  };

  const handleCategoryAdded = async () => {
    try {
      const categoriesData = await categoriesService.getAll();
      setCategories(categoriesData);
      setShowAddCategoryModal(false);
    } catch (error) {
      console.error('Error reloading categories:', error);
      toast.error('Failed to reload categories');
    }
  };

  const handleLocationAdded = async () => {
    try {
      const locationsData = await locationsService.getAll();
      setLocations(locationsData);
      setShowAddLocationModal(false);
    } catch (error) {
      console.error('Error reloading locations:', error);
      toast.error('Failed to reload locations');
    }
  };

  const updateProperty = (key: string, value: string) => {
    setAdditionalProperties(prev => ({
      ...prev,
      [key]: value
    }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!part) {
    return (
      <div className="text-center py-12">
        <Package className="mx-auto h-12 w-12 text-muted" />
        <h3 className="mt-2 text-sm font-medium text-secondary">Part not found</h3>
        <p className="mt-1 text-sm text-muted">The requested part could not be found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate(`/parts/${id}`)}
            className="btn btn-ghost p-2"
          >
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
              console.log('Save button clicked');
              console.log('Form errors:', Object.keys(errors).length > 0 ? 
                Object.fromEntries(Object.entries(errors).map(([key, error]) => [key, error?.message])) : 
                'No errors'
              );
              console.log('Form isValid:', isValid);
              console.log('Form values:', watch());
              handleSubmit(onSubmit)();
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
        {/* Hidden input to register image_url field */}
        <input type="hidden" {...register('image_url')} />
        
        {/* Basic Information */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              label="Name"
              error={errors.name?.message}
              required
            >
              <input
                {...register('name')}
                className="input w-full"
                placeholder="Enter part name"
              />
            </FormField>

            <FormField
              label="Part Number"
              error={errors.part_number?.message}
            >
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              label="Quantity"
              error={errors.quantity?.message}
              required
            >
              <input
                {...register('quantity', { valueAsNumber: true })}
                type="number"
                min="0"
                className="input w-full"
                placeholder="0"
              />
            </FormField>

            <FormField
              label="Minimum Quantity"
              error={errors.minimum_quantity?.message}
            >
              <input
                {...register('minimum_quantity', { valueAsNumber: true })}
                type="number"
                min="0"
                className="input w-full"
                placeholder="0"
              />
            </FormField>

            <LocationTreeSelector
              selectedLocationId={watch('location_id')}
              onLocationSelect={(locationId) => setValue('location_id', locationId || '')}
              onAddNewLocation={() => setShowAddLocationModal(true)}
              label="Location"
              description="Select where this part is stored"
              error={errors.location_id?.message}
              showAddButton={true}
              compact={false}
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

        {/* Supplier Information */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Supplier Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              label="Supplier"
              error={errors.supplier?.message}
            >
              <input
                {...register('supplier')}
                className="input w-full"
                placeholder="Enter supplier name"
              />
            </FormField>

            <FormField
              label="Supplier URL"
              error={errors.supplier_url?.message}
            >
              <input
                {...register('supplier_url')}
                type="url"
                className="input w-full"
                placeholder="https://supplier.com/part-page"
              />
            </FormField>
          </div>
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
          </div>
        </div>

        {/* Additional Properties */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-primary">Additional Properties</h2>
            <span className="text-sm text-secondary bg-background-secondary px-2 py-1 rounded">
              {Object.keys(additionalProperties).length} properties
            </span>
          </div>
          
          {/* Existing Properties */}
          {Object.keys(additionalProperties).length > 0 && (
            <div className="space-y-3 mb-6">
              {Object.entries(additionalProperties).map(([key, value]) => (
                <div key={key} className="flex items-center gap-3 p-3 bg-background-secondary rounded-lg">
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

          {/* Info */}
          <div className="mt-4 p-3 bg-info/10 border border-info/20 rounded-lg">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-info mt-0.5 flex-shrink-0" />
              <div className="text-sm text-primary">
                <p className="font-medium mb-1">Additional Properties</p>
                <p className="text-secondary">
                  Store custom metadata like technical specifications, part ratings, or any other relevant information. 
                  These properties are automatically populated during CSV imports with enrichment data.
                </p>
              </div>
            </div>
          </div>
        </div>
      </form>

      {/* Modals */}
      <AddCategoryModal
        isOpen={showAddCategoryModal}
        onClose={() => setShowAddCategoryModal(false)}
        onSuccess={handleCategoryAdded}
        existingCategories={categories.map(cat => cat.name)}
      />
      
      <AddLocationModal
        isOpen={showAddLocationModal}
        onClose={() => setShowAddLocationModal(false)}
        onSuccess={handleLocationAdded}
      />
    </div>
  );
};

export default EditPartPage;