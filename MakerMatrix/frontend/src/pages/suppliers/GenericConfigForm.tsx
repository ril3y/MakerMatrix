/**
 * Generic Supplier Configuration Form
 * 
 * Generic configuration form for suppliers that use standard API setup fields.
 */

import React from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface GenericConfigFormProps {
  config: any;
  onConfigChange: (field: string, value: any) => void;
  errors: string[];
  supplierType: string;
}

export const GenericConfigForm: React.FC<GenericConfigFormProps> = ({
  config,
  onConfigChange,
  errors,
  supplierType
}) => {
  const capabilities = [
    { key: 'fetch_datasheet', label: 'Datasheet Download', description: 'Download component datasheets' },
    { key: 'fetch_image', label: 'Image Download', description: 'Download component images' },
    { key: 'fetch_pricing', label: 'Pricing Information', description: 'Retrieve current pricing data' },
    { key: 'fetch_stock', label: 'Stock Information', description: 'Check availability and stock levels' },
    { key: 'fetch_specifications', label: 'Technical Specifications', description: 'Retrieve detailed component specifications' },
    { key: 'fetch_alternatives', label: 'Alternative Parts', description: 'Find alternative/substitute parts' },
    { key: 'fetch_lifecycle_status', label: 'Lifecycle Status', description: 'Get part lifecycle and availability status' },
    { key: 'validate_part_number', label: 'Part Validation', description: 'Validate part numbers and existence' }
  ];

  const handleCapabilityChange = (capability: string, enabled: boolean) => {
    // Map capability keys to database field names
    const capabilityFieldMap = {
      'fetch_datasheet': 'supports_datasheet',
      'fetch_image': 'supports_image',
      'fetch_pricing': 'supports_pricing',
      'fetch_stock': 'supports_stock',
      'fetch_specifications': 'supports_specifications',
      'fetch_alternatives': 'supports_alternatives',
      'fetch_lifecycle_status': 'supports_lifecycle_status',
      'validate_part_number': 'supports_part_validation'
    };
    
    const field = capabilityFieldMap[capability] || `supports_${capability.replace('fetch_', '')}`;
    onConfigChange(field, enabled);
  };

  const handleCustomHeaderChange = (key: string, value: string) => {
    const newHeaders = { ...config.custom_headers };
    if (value.trim()) {
      newHeaders[key] = value;
    } else {
      delete newHeaders[key];
    }
    onConfigChange('custom_headers', newHeaders);
  };

  const addCustomHeader = () => {
    const key = prompt('Enter header name:');
    if (key && key.trim()) {
      handleCustomHeaderChange(key.trim(), '');
    }
  };

  return (
    <div className="space-y-6">
      {/* Basic Information */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Basic Information
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Supplier Name *
            </label>
            <input
              type="text"
              value={config.supplier_name}
              onChange={(e) => onConfigChange('supplier_name', e.target.value)}
              placeholder="lcsc, digikey, etc."
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              disabled={supplierType !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Lowercase letters, numbers, hyphens, and underscores only
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Display Name *
            </label>
            <input
              type="text"
              value={config.display_name}
              onChange={(e) => onConfigChange('display_name', e.target.value)}
              placeholder="LCSC Electronics"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={config.description}
              onChange={(e) => onConfigChange('description', e.target.value)}
              placeholder="Brief description of the supplier"
              rows={2}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* API Configuration */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          API Configuration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Base URL *
            </label>
            <input
              type="url"
              value={config.base_url}
              onChange={(e) => onConfigChange('base_url', e.target.value)}
              placeholder="https://api.example.com"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              API Type
            </label>
            <select
              value={config.api_type}
              onChange={(e) => onConfigChange('api_type', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="rest">REST API</option>
              <option value="graphql">GraphQL</option>
              <option value="scraping">Web Scraping</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              API Version
            </label>
            <input
              type="text"
              value={config.api_version}
              onChange={(e) => onConfigChange('api_version', e.target.value)}
              placeholder="v1"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rate Limit (per minute)
            </label>
            <input
              type="number"
              value={config.rate_limit_per_minute || ''}
              onChange={(e) => onConfigChange('rate_limit_per_minute', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="60"
              min="1"
              max="10000"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Timeout (seconds)
            </label>
            <input
              type="number"
              value={config.timeout_seconds}
              onChange={(e) => onConfigChange('timeout_seconds', parseInt(e.target.value))}
              min="1"
              max="300"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max Retries
            </label>
            <input
              type="number"
              value={config.max_retries}
              onChange={(e) => onConfigChange('max_retries', parseInt(e.target.value))}
              min="0"
              max="10"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Capabilities */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Supported Capabilities
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {capabilities.map((capability) => {
            const field = `supports_${capability.key.replace('fetch_', '')}`;
            const isEnabled = config[field];
            
            return (
              <label key={capability.key} className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={(e) => handleCapabilityChange(capability.key, e.target.checked)}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {capability.label}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {capability.description}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* Custom Headers */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Custom Headers
          </h3>
          <button
            onClick={addCustomHeader}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
          >
            Add Header
          </button>
        </div>
        <div className="space-y-2">
          {Object.entries(config.custom_headers || {}).map(([key, value]) => (
            <div key={key} className="flex items-center space-x-2">
              <input
                type="text"
                value={key}
                readOnly
                className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => handleCustomHeaderChange(key, e.target.value)}
                placeholder="Header value"
                className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <button
                onClick={() => handleCustomHeaderChange(key, '')}
                className="text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          {Object.keys(config.custom_headers || {}).length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">
              No custom headers configured
            </p>
          )}
        </div>
      </div>

      {/* Warning about credentials */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
        <div className="flex">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Next Step: Add Credentials
            </h3>
            <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
              After creating this configuration, you'll need to add your API credentials 
              using the "Manage Credentials" button.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};