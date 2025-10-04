/**
 * DigiKey-Specific Configuration Form
 * 
 * Custom configuration form for DigiKey API setup with their specific requirements.
 */

import React from 'react';
import { HelpCircle, AlertTriangle } from 'lucide-react';
import { CustomSelect } from '@/components/ui/CustomSelect';

interface DigiKeyConfigFormProps {
  config: any;
  onConfigChange: (field: string, value: any) => void;
  errors: string[];
}

export const DigiKeyConfigForm: React.FC<DigiKeyConfigFormProps> = ({
  config,
  onConfigChange,
  errors
}) => {
  return (
    <div className="space-y-6">
      {/* DigiKey Setup Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
        <div className="flex">
          <HelpCircle className="w-5 h-5 text-blue-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              DigiKey API Setup Instructions
            </h3>
            <div className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              <ol className="list-decimal list-inside space-y-1">
                <li>Register an app at <a href="https://developer.digikey.com" target="_blank" rel="noopener noreferrer" className="underline">developer.digikey.com</a></li>
                <li>Set OAuth callback URL to: <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">https://localhost:8443/api/suppliers/digikey/oauth/callback</code></li>
                <li>Get your Client ID and Client Secret from the app settings</li>
                <li>Configure the settings below</li>
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
              value={config.supplier_name || 'digikey'}
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
              value={config.display_name || 'DigiKey Electronics'}
              onChange={(e) => onConfigChange('display_name', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={config.description || 'Global electronic components distributor'}
              onChange={(e) => onConfigChange('description', e.target.value)}
              rows={2}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* DigiKey Specific Configuration */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          DigiKey API Configuration
        </h3>
        <div className="space-y-4">
          {/* Environment Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Environment Mode *
            </label>
            <CustomSelect
              value={config.sandbox_mode !== false ? 'sandbox' : 'production'}
              onChange={(val) => onConfigChange('sandbox_mode', val === 'sandbox')}
              options={[
                { value: 'sandbox', label: 'Sandbox (Testing) - api-sandbox.digikey.com' },
                { value: 'production', label: 'Production - api.digikey.com' }
              ]}
              placeholder="Select environment mode"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Sandbox mode is safe for testing. Use production only with valid production credentials.
            </p>
            {config.sandbox_mode === false && (
              <div className="mt-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                <div className="flex">
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                  <div className="ml-3">
                    <p className="text-sm text-yellow-700 dark:text-yellow-300">
                      <strong>Production Mode:</strong> You are using the live DigiKey API. Make sure you have valid production credentials.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* OAuth Callback URL */}
          <div>
            <div className="flex items-center space-x-1 mb-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                OAuth Callback URL *
              </label>
              <div className="group relative">
                <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-80 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 pointer-events-none">
                  This must exactly match the callback URL registered in your DigiKey app settings at developer.digikey.com
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
            <input
              type="url"
              value={config.oauth_callback_url || 'https://localhost:8443/api/suppliers/digikey/oauth/callback'}
              onChange={(e) => onConfigChange('oauth_callback_url', e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Default: https://localhost:8443/api/suppliers/digikey/oauth/callback
            </p>
          </div>

          {/* Token Storage Path */}
          <div>
            <div className="flex items-center space-x-1 mb-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Token Storage Path *
              </label>
              <div className="group relative">
                <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-80 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 pointer-events-none">
                  Directory path where OAuth tokens will be cached. Use absolute path. Tokens are stored here to avoid re-authentication.
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
            <input
              type="text"
              value={config.storage_path || '/tmp/digikey_cache'}
              onChange={(e) => onConfigChange('storage_path', e.target.value)}
              placeholder="/path/to/digikey/cache"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              required
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Default: /tmp/digikey_cache
            </p>
          </div>
        </div>
      </div>

      {/* Capabilities - Auto-configured for DigiKey */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          DigiKey Capabilities (Auto-configured)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {[
            { key: 'datasheet', label: 'Datasheet Download', description: 'Download component datasheets' },
            { key: 'image', label: 'Image Download', description: 'Download component images' },
            { key: 'pricing', label: 'Pricing Information', description: 'Retrieve current pricing data' },
            { key: 'stock', label: 'Stock Information', description: 'Check availability and stock levels' },
            { key: 'specifications', label: 'Technical Specifications', description: 'Retrieve detailed component specifications' }
          ].map((capability) => (
            <div key={capability.key} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={true}
                disabled
                className="h-4 w-4 text-blue-600 border-gray-300 rounded opacity-50"
              />
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {capability.label}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {capability.description}
                </div>
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">
          DigiKey capabilities are automatically configured based on their API features.
        </p>
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
              After creating this configuration, you'll need to add your DigiKey Client ID and Client Secret 
              using the "Manage Credentials" button.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};