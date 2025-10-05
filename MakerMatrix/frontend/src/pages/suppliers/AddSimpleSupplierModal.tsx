/**
 * Add Simple Supplier Modal
 *
 * Modal for quickly adding simple suppliers (like NewEgg.com) that don't have API integration.
 * Only requires name and website URL - automatically fetches favicon.
 */

import React, { useState, useEffect } from 'react';
import { X, Plus, CheckCircle, AlertTriangle, Link as LinkIcon } from 'lucide-react';
import { supplierService } from '../../services/supplier.service';

interface AddSimpleSupplierModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const AddSimpleSupplierModal: React.FC<AddSimpleSupplierModalProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    supplier_name: '',
    display_name: '',
    website_url: '',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [websiteUrlManuallyEdited, setWebsiteUrlManuallyEdited] = useState(false);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;

    // If user manually edits website_url, mark it as edited
    if (name === 'website_url') {
      setWebsiteUrlManuallyEdited(true);
    }

    setFormData(prev => ({ ...prev, [name]: value }));

    // Auto-fill website_url from display_name if not manually edited
    if (name === 'display_name' && !websiteUrlManuallyEdited && value.trim()) {
      // Extract just the company name (remove common suffixes like "Electronics", ".com", etc.)
      const cleanCompanyName = value
        .toLowerCase()
        .replace(/\s*(electronics|store|shop|inc|llc|corporation|corp)\.?\s*$/i, '')
        .trim()
        .replace(/[^a-z0-9]/g, '');

      if (cleanCompanyName) {
        setFormData(prev => ({ ...prev, website_url: `https://${cleanCompanyName}.com` }));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    // Validation
    if (!formData.display_name.trim()) {
      setError('Display name is required');
      return;
    }

    if (!formData.website_url.trim()) {
      setError('Website URL is required');
      return;
    }

    // Validate URL format
    try {
      new URL(formData.website_url.startsWith('http') ? formData.website_url : `https://${formData.website_url}`);
    } catch {
      setError('Invalid website URL format');
      return;
    }

    try {
      setLoading(true);

      // Create supplier config
      const supplierConfig = {
        supplier_name: formData.supplier_name || formData.display_name.toLowerCase().replace(/[^a-z0-9]/g, '_'),
        display_name: formData.display_name,
        description: formData.description || `Simple supplier: ${formData.display_name}`,
        website_url: formData.website_url.startsWith('http') ? formData.website_url : `https://${formData.website_url}`,
        supplier_type: 'simple',
        api_type: 'rest',  // Default to rest but won't be used for simple suppliers
        base_url: '',  // Not needed for simple suppliers
        enabled: true,
        supports_datasheet: false,
        supports_image: false,
        supports_pricing: false,
        supports_stock: false,
        supports_specifications: false
      };

      console.log('Creating simple supplier:', supplierConfig);
      await supplierService.createSupplier(supplierConfig);

      setSuccess(true);

      // Wait a moment to show success message, then close
      setTimeout(() => {
        onSuccess();
      }, 1500);

    } catch (err: any) {
      console.error('Failed to create simple supplier:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create supplier';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-8">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 dark:bg-green-900 mb-4">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Supplier Added Successfully!
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Favicon will be automatically downloaded if available.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Add Simple Supplier
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Add a supplier without API integration (e.g., NewEgg, Amazon)
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h4>
                <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Display Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="display_name"
              value={formData.display_name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., NewEgg Electronics"
              required
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              The name that will be displayed in the UI
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Website URL <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <LinkIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                name="website_url"
                value={formData.website_url}
                onChange={handleChange}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="https://www.costco.com"
                required
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Auto-populated from name. Favicon will be automatically downloaded.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Optional description..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300
                       rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                       disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Add Supplier
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
