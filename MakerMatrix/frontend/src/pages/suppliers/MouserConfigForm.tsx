/**
 * Mouser-Specific Configuration Form
 * 
 * Custom configuration form for Mouser API setup with their specific requirements.
 */

import React from 'react';
import { HelpCircle, AlertTriangle } from 'lucide-react';

interface MouserConfigFormProps {
  config: any;
  onConfigChange: (field: string, value: any) => void;
  errors: string[];
}

export const MouserConfigForm: React.FC<MouserConfigFormProps> = ({
  config,
  onConfigChange,
  errors
}) => {
  return (
    <div className="space-y-6">
      {/* Mouser Setup Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
        <div className="flex">
          <HelpCircle className="w-5 h-5 text-blue-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Mouser API Setup Instructions
            </h3>
            <div className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              <ol className="list-decimal list-inside space-y-1">
                <li>Register for an account at <a href="https://mouser.com" target="_blank" rel="noopener noreferrer" className="underline">mouser.com</a></li>
                <li>Apply for API access through Mouser's API portal</li>
                <li>Get your API key from Mouser support</li>
                <li>Review API documentation at <a href="https://api.mouser.com/api/docs/ui/index" target="_blank" rel="noopener noreferrer" className="underline">api.mouser.com/api/docs</a></li>
              </ol>
            </div>
          </div>
        </div>
      </div>

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
              value={config.supplier_name || 'mouser'}
              onChange={(e) => onConfigChange('supplier_name', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              disabled
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
              value={config.display_name || 'Mouser Electronics'}
              onChange={(e) => onConfigChange('display_name', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={config.description || 'Electronic component distributor with comprehensive inventory and global shipping'}
              onChange={(e) => onConfigChange('description', e.target.value)}
              rows={2}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Mouser API Configuration */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Mouser API Configuration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Base URL *
            </label>
            <input
              type="url"
              value={config.base_url || 'https://api.mouser.com'}
              onChange={(e) => onConfigChange('base_url', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              API Version
            </label>
            <input
              type="text"
              value={config.api_version || 'v1'}
              onChange={(e) => onConfigChange('api_version', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rate Limit (per minute)
            </label>
            <input
              type="number"
              value={config.rate_limit_per_minute || 1000}
              onChange={(e) => onConfigChange('rate_limit_per_minute', parseInt(e.target.value))}
              min="1"
              max="10000"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Mouser typically allows high rate limits
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Timeout (seconds)
            </label>
            <input
              type="number"
              value={config.timeout_seconds || 30}
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
              value={config.max_retries || 3}
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
          Mouser Capabilities
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {[
            { key: 'datasheet', label: 'Datasheet Download', description: 'Download component datasheets', default: true },
            { key: 'image', label: 'Image Download', description: 'Download component images', default: true },
            { key: 'pricing', label: 'Pricing Information', description: 'Retrieve current pricing data', default: true },
            { key: 'stock', label: 'Stock Information', description: 'Check availability and stock levels', default: true },
            { key: 'specifications', label: 'Technical Specifications', description: 'Retrieve detailed component specifications', default: true }
          ].map((capability) => (
            <label key={capability.key} className="flex items-start space-x-3">
              <input
                type="checkbox"
                checked={config[`supports_${capability.key}`] !== false}
                onChange={(e) => onConfigChange(`supports_${capability.key}`, e.target.checked)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {capability.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {capability.description}
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Custom Headers */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Custom Headers
        </h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value="Accept"
              readOnly
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
            />
            <input
              type="text"
              value="application/json"
              readOnly
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
            />
          </div>
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value="Content-Type"
              readOnly
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
            />
            <input
              type="text"
              value="application/json"
              readOnly
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
            />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 italic">
            Standard headers are pre-configured for Mouser API compatibility.
          </p>
        </div>
      </div>

      {/* Warning about credentials */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
        <div className="flex">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Next Step: Add API Key
            </h3>
            <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
              After creating this configuration, you'll need to add your Mouser API key 
              using the "Manage Credentials" button.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};