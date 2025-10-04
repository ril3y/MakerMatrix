/**
 * Transfer Quantity Modal
 *
 * Modal for transferring part quantities between locations
 * Supports both existing location transfers and creating new cassettes
 */

import { useState, useEffect } from 'react';
import { ArrowRightLeft, Package, MapPin } from 'lucide-react';
import CrudModal from '@/components/ui/CrudModal';
import { FormInput, FormField } from '@/components/forms';
import { CustomSelect } from '@/components/ui/CustomSelect';
import { useModalFormWithValidation } from '@/hooks/useFormWithValidation';
import { partAllocationService, PartAllocation, TransferRequest } from '@/services/part-allocation.service';
import { locationsService } from '@/services/locations.service';
import { Location } from '@/types/locations';
import toast from 'react-hot-toast';
import { z } from 'zod';

interface TransferQuantityModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  partId: string;
  partName: string;
  sourceAllocation: PartAllocation;
}

// Transfer form schema
const transferFormSchema = z.object({
  to_location_id: z.string().min(1, 'Destination location is required'),
  quantity: z.number()
    .min(1, 'Quantity must be at least 1')
    .int('Quantity must be a whole number'),
  notes: z.string().optional(),
});

type TransferFormData = z.infer<typeof transferFormSchema>;

const TransferQuantityModal = ({
  isOpen,
  onClose,
  onSuccess,
  partId,
  partName,
  sourceAllocation,
}: TransferQuantityModalProps) => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Form with validation
  const form = useModalFormWithValidation<TransferFormData>({
    schema: transferFormSchema.refine(
      (data) => data.quantity <= sourceAllocation.quantity_at_location,
      {
        message: `Cannot transfer more than ${sourceAllocation.quantity_at_location} (available at source)`,
        path: ['quantity'],
      }
    ),
    isOpen,
    onClose,
    defaultValues: {
      to_location_id: '',
      quantity: 1,
      notes: undefined,
    },
    onSubmit: handleFormSubmit,
    onSuccess: () => {
      onSuccess();
      handleClose();
    },
    successMessage: 'Quantity transferred successfully',
  });

  useEffect(() => {
    if (isOpen) {
      loadLocations();
    }
  }, [isOpen]);

  const loadLocations = async () => {
    try {
      setLoadingLocations(true);
      const allLocations = await locationsService.getAllLocations();
      console.log('All locations loaded:', allLocations.length, allLocations);
      console.log('Source location ID:', sourceAllocation.location_id);

      // Filter out the source location from destination options
      const filteredLocations = allLocations.filter(
        (loc) => loc.id !== sourceAllocation.location_id
      );
      console.log('Filtered locations (after removing source):', filteredLocations.length, filteredLocations);

      setLocations(filteredLocations);
    } catch (error) {
      console.error('Failed to load locations:', error);
      toast.error('Failed to load locations');
    } finally {
      setLoadingLocations(false);
    }
  };

  // Handle form submission
  async function handleFormSubmit(data: TransferFormData) {
    const request: TransferRequest = {
      from_location_id: sourceAllocation.location_id,
      to_location_id: data.to_location_id,
      quantity: data.quantity,
      notes: data.notes,
    };

    return await partAllocationService.transferQuantity(partId, request);
  }

  const handleClose = () => {
    form.reset();
    onClose();
  };

  // Build hierarchical display for destination locations
  const buildLocationHierarchy = (locs: Location[]): Array<{id: string, name: string, level: number, path: string}> => {
    const result: Array<{id: string, name: string, level: number, path: string}> = [];
    const locationMap = new Map<string, Location>();
    locs.forEach(loc => locationMap.set(loc.id, loc));

    const buildPath = (loc: Location): string => {
      if (loc.parent_id) {
        const parent = locationMap.get(loc.parent_id);
        if (parent) {
          return buildPath(parent) + ' → ' + loc.name;
        }
      }
      return loc.name;
    };

    const addLocation = (location: Location, level: number = 0) => {
      result.push({
        id: location.id,
        name: location.name,
        level,
        path: buildPath(location),
      });

      const children = locs.filter(loc => loc.parent_id === location.id);
      children
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(child => addLocation(child, level + 1));
    };

    // Treat locations as roots if they have no parent OR if their parent is not in the filtered list
    // This handles the case where we filtered out the source location and some locations had it as parent
    const rootLocations = locs
      .filter(loc => !loc.parent_id || !locationMap.has(loc.parent_id))
      .sort((a, b) => a.name.localeCompare(b.name));

    rootLocations.forEach(loc => addLocation(loc));

    return result;
  };

  const hierarchicalLocations = buildLocationHierarchy(locations);
  console.log('Hierarchical locations for dropdown:', hierarchicalLocations);
  const maxQuantity = sourceAllocation.quantity_at_location;

  return (
    <CrudModal
      isOpen={isOpen}
      onClose={handleClose}
      title="Transfer Quantity"
      size="md"
      mode="create"
      onSubmit={form.onSubmit}
      loading={form.loading}
      loadingText="Transferring..."
      submitText="Transfer"
    >
      {loadingLocations ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-theme-secondary mt-2">Loading locations...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Part Info */}
          <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
            <div className="flex items-center space-x-2 mb-2">
              <Package className="w-4 h-4 text-theme-muted" />
              <span className="text-sm font-medium text-theme-primary">Part</span>
            </div>
            <p className="text-sm text-theme-primary font-semibold">{partName}</p>
          </div>

          {/* Source Location (Read-only) */}
          <div className="p-4 bg-theme-secondary rounded-lg border border-theme-primary">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-theme-muted" />
                <span className="text-sm font-medium text-theme-primary">From Location</span>
              </div>
              <ArrowRightLeft className="w-4 h-4 text-theme-muted" />
            </div>
            <div className="flex items-center space-x-3">
              {sourceAllocation.location?.emoji && (
                <span className="text-2xl">{sourceAllocation.location.emoji}</span>
              )}
              <div className="flex-1">
                <p className="text-sm font-medium text-theme-primary">
                  {sourceAllocation.location?.name || 'Unknown Location'}
                </p>
                {sourceAllocation.location_path && (
                  <p className="text-xs text-theme-muted">{sourceAllocation.location_path}</p>
                )}
                <p className="text-xs text-theme-secondary mt-1">
                  Available: <span className="font-semibold">{maxQuantity.toLocaleString()}</span>
                </p>
              </div>
            </div>
          </div>

          {/* DEBUG: Show location counts */}
          <div className="p-3 bg-yellow-100 dark:bg-yellow-900/20 border border-yellow-500 rounded text-xs">
            <strong>DEBUG:</strong> Total locations loaded: {locations.length} |
            Hierarchical locations: {hierarchicalLocations.length} |
            Source location: {sourceAllocation.location?.name} ({sourceAllocation.location_id})
          </div>

          {/* Destination Location Selector */}
          <FormField
            label="To Location"
            description="Select the destination location for this transfer"
            error={form.getFieldError('to_location_id')}
            required
          >
            <CustomSelect
              value={form.watch('to_location_id') || ''}
              onChange={(value) => form.setValue('to_location_id', value)}
              options={hierarchicalLocations.map((loc) => ({
                value: loc.id,
                label: `${'  '.repeat(loc.level)}${loc.level > 0 ? '└─ ' : ''}${loc.name}`
              }))}
              placeholder="Select destination location..."
              error={form.getFieldError('to_location_id')}
              searchable={true}
              searchPlaceholder="Search locations..."
            />
          </FormField>

          {/* Quantity Input */}
          <FormInput
            label="Quantity to Transfer"
            type="number"
            placeholder="Enter quantity"
            required
            min={1}
            max={maxQuantity}
            registration={form.register('quantity', {
              valueAsNumber: true,
              min: 1,
              max: maxQuantity,
            })}
            error={form.getFieldError('quantity')}
            description={`Maximum: ${maxQuantity.toLocaleString()}`}
          />

          {/* Quantity Slider */}
          <div className="px-1">
            <input
              type="range"
              min={1}
              max={maxQuantity}
              value={form.watch('quantity') || 1}
              onChange={(e) => form.setValue('quantity', parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-theme-muted mt-1">
              <span>1</span>
              <span>{maxQuantity.toLocaleString()}</span>
            </div>
          </div>

          {/* Transfer Preview */}
          {form.watch('quantity') > 0 && form.watch('to_location_id') && (
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-theme-primary mb-2 font-medium">Transfer Summary:</p>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-theme-muted">Transferring:</span>
                  <span className="font-semibold text-theme-primary">
                    {form.watch('quantity')?.toLocaleString() || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-theme-muted">Remaining at source:</span>
                  <span className="font-semibold text-theme-primary">
                    {(maxQuantity - (form.watch('quantity') || 0)).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          <FormField
            label="Notes"
            description="Optional notes about this transfer"
          >
            <textarea
              {...form.register('notes')}
              placeholder="Enter any notes about this transfer..."
              rows={3}
              className="w-full px-3 py-2 border border-theme-primary rounded-md bg-background-primary text-theme-primary focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
            {form.getFieldError('notes') && (
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                {form.getFieldError('notes')}
              </p>
            )}
          </FormField>
        </div>
      )}
    </CrudModal>
  );
};

export default TransferQuantityModal;
