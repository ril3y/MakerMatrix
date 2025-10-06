/**
 * Supplier Selector Component
 *
 * Dropdown selector for configured suppliers with option to add custom supplier
 */

import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { supplierService, SupplierConfig } from '@/services/supplier.service';
import { CustomSelect } from './CustomSelect';
import toast from 'react-hot-toast';

interface SupplierSelectorProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  placeholder?: string;
  disabled?: boolean;
}

export const SupplierSelector = ({
  value,
  onChange,
  error,
  placeholder = 'Select supplier...',
  disabled = false
}: SupplierSelectorProps) => {
  const [suppliers, setSuppliers] = useState<SupplierConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customSupplier, setCustomSupplier] = useState('');

  useEffect(() => {
    loadSuppliers();
  }, []);

  useEffect(() => {
    // Check if current value is a custom supplier (not in the list)
    if (value && suppliers.length > 0) {
      const isConfigured = suppliers.some(
        s => s.supplier_name.toLowerCase() === value.toLowerCase() ||
             s.display_name.toLowerCase() === value.toLowerCase()
      );
      if (!isConfigured) {
        setShowCustomInput(true);
        setCustomSupplier(value);
      }
    }
  }, [value, suppliers]);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      const data = await supplierService.getSuppliers(true); // Get only enabled suppliers
      setSuppliers(data);
    } catch (err) {
      console.error('Failed to load suppliers:', err);
      toast.error('Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectChange = (selectedValue: string) => {
    if (selectedValue === '__custom__') {
      setShowCustomInput(true);
      setCustomSupplier('');
      onChange('');
    } else {
      setShowCustomInput(false);
      setCustomSupplier('');
      onChange(selectedValue);
    }
  };

  const extractDomainFromUrl = (input: string): string | null => {
    try {
      // Check if input looks like a URL
      const urlPattern = /^https?:\/\//i;
      if (!urlPattern.test(input)) {
        return null;
      }

      const url = new URL(input);
      const hostname = url.hostname;

      // Remove www. prefix if present
      const domain = hostname.replace(/^www\./, '');

      // Extract base domain (e.g., ebay.com from subdomain.ebay.com)
      const parts = domain.split('.');
      if (parts.length >= 2) {
        return parts.slice(-2).join('.');
      }

      return domain;
    } catch (err) {
      return null;
    }
  };

  const handleCustomInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;

    // Check if user pasted a URL
    const domain = extractDomainFromUrl(newValue);
    if (domain) {
      // Extract supplier name from domain (e.g., "ebay" from "ebay.com")
      const supplierName = domain.split('.')[0];
      setCustomSupplier(supplierName);
      onChange(supplierName);
      toast.success(`Detected supplier: ${supplierName} from URL`);
    } else {
      setCustomSupplier(newValue);
      onChange(newValue);
    }
  };

  const handleCancelCustom = () => {
    setShowCustomInput(false);
    setCustomSupplier('');
    onChange('');
  };

  if (loading) {
    return (
      <div className="relative">
        <div className="w-full px-3 py-2 border border-theme-primary rounded-md bg-theme-primary flex items-center justify-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (showCustomInput) {
    return (
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={customSupplier}
            onChange={handleCustomInputChange}
            placeholder="Enter supplier name or paste product URL..."
            disabled={disabled}
            className={`
              flex-1 px-3 py-2 border rounded-md
              bg-theme-primary text-theme-primary
              focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
              disabled:bg-theme-tertiary disabled:text-theme-muted disabled:cursor-not-allowed
              ${error ? 'border-red-500' : 'border-theme-primary'}
            `}
            autoFocus
          />
          <button
            type="button"
            onClick={handleCancelCustom}
            className="btn btn-secondary px-3"
            disabled={disabled}
          >
            Cancel
          </button>
        </div>
        <p className="text-xs text-theme-muted">
          Paste a product URL to auto-detect supplier, or enter a custom supplier name
        </p>
      </div>
    );
  }

  // Build option groups for CustomSelect
  const optionGroups = [];

  // Add custom supplier option FIRST
  optionGroups.push({
    label: 'Add Supplier',
    options: [{ value: '__custom__', label: '+ Add Custom Supplier...' }]
  });

  // Then add configured suppliers
  if (suppliers.length > 0) {
    optionGroups.push({
      label: 'Configured Suppliers',
      options: suppliers.map(supplier => ({
        value: supplier.supplier_name,
        label: supplier.display_name,
        image_url: supplier.image_url
      }))
    });
  }

  return (
    <CustomSelect
      value={value || ''}
      onChange={handleSelectChange}
      optionGroups={optionGroups}
      placeholder={placeholder}
      disabled={disabled}
      error={error}
      searchable={true}
      searchPlaceholder="Search suppliers..."
    />
  );
};

export default SupplierSelector;
