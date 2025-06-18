/**
 * Edit Supplier Configuration Modal
 * 
 * Modal for editing existing supplier configurations with validation and capability management.
 */

import React, { useState } from 'react';
import { X, AlertTriangle, Save, TestTube } from 'lucide-react';
import { supplierService, SupplierConfig, SupplierConfigUpdate, ConnectionTestResult } from '../../services/supplier.service';

interface EditSupplierModalProps {
  supplier: SupplierConfig;
  onClose: () => void;
  onSuccess: () => void;
}

export const EditSupplierModal: React.FC<EditSupplierModalProps> = ({ supplier, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [successMessage, setSuccessMessage] = useState<string>('');
  
  const [config, setConfig] = useState<SupplierConfigUpdate>({
    display_name: supplier.display_name,
    description: supplier.description || '',
    api_type: supplier.api_type,
    base_url: supplier.base_url,
    api_version: supplier.api_version || '',
    rate_limit_per_minute: supplier.rate_limit_per_minute || (supplier.supplier_name === 'LCSC' ? 300 : null),
    timeout_seconds: supplier.timeout_seconds,
    max_retries: supplier.max_retries,
    retry_backoff: supplier.retry_backoff,
    enabled: supplier.enabled,
    supports_datasheet: supplier.capabilities.includes('fetch_datasheet'),
    supports_image: supplier.capabilities.includes('fetch_image'),
    supports_pricing: supplier.capabilities.includes('fetch_pricing'),
    supports_stock: supplier.capabilities.includes('fetch_stock'),
    supports_specifications: supplier.capabilities.includes('fetch_specifications'),
    custom_headers: supplier.custom_headers,
    custom_parameters: supplier.custom_parameters
  });

  const capabilities = supplierService.getSupportedCapabilities();

  const handleConfigChange = (field: keyof SupplierConfigUpdate, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setErrors([]); // Clear errors when user makes changes
  };

  const handleCapabilityChange = (capability: string, enabled: boolean) => {
    const field = `supports_${capability.replace('fetch_', '')}` as keyof SupplierConfigUpdate;
    handleConfigChange(field, enabled);
  };

  const handleCustomHeaderChange = (key: string, value: string) => {
    const newHeaders = { ...config.custom_headers };
    if (value.trim()) {
      newHeaders[key] = value;
    } else {
      delete newHeaders[key];
    }
    handleConfigChange('custom_headers', newHeaders);
  };

  const addCustomHeader = () => {
    const key = prompt('Enter header name:');
    if (key && key.trim()) {
      handleCustomHeaderChange(key.trim(), '');
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      const result = await supplierService.testConnection(supplier.supplier_name);
      setTestResult(result);
    } catch (err: any) {
      setTestResult({
        supplier_name: supplier.supplier_name,
        success: false,
        test_duration_seconds: 0,
        tested_at: new Date().toISOString(),
        error_message: err.response?.data?.detail || 'Connection test failed'
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setErrors([]);
      setSuccessMessage('');

      // Validate configuration
      const validationErrors = supplierService.validateConfig(config, supplier.supplier_name);
      if (validationErrors.length > 0) {
        setErrors(validationErrors);
        return;
      }

      // Update supplier
      await supplierService.updateSupplier(supplier.supplier_name, config);
      
      // Show success message briefly before closing
      setSuccessMessage('Configuration saved successfully!');
      setTimeout(() => {
        onSuccess();
      }, 1000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to update supplier configuration';
      setErrors([errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const hasChanges = () => {
    const originalConfig = {
      display_name: supplier.display_name,
      description: supplier.description || '',
      api_type: supplier.api_type,
      base_url: supplier.base_url,
      api_version: supplier.api_version || '',
      rate_limit_per_minute: supplier.rate_limit_per_minute,
      timeout_seconds: supplier.timeout_seconds,
      max_retries: supplier.max_retries,
      retry_backoff: supplier.retry_backoff,
      enabled: supplier.enabled,
      supports_datasheet: supplier.capabilities.includes('fetch_datasheet'),
      supports_image: supplier.capabilities.includes('fetch_image'),
      supports_pricing: supplier.capabilities.includes('fetch_pricing'),
      supports_stock: supplier.capabilities.includes('fetch_stock'),
      supports_specifications: supplier.capabilities.includes('fetch_specifications'),
      custom_headers: supplier.custom_headers,
      custom_parameters: supplier.custom_parameters
    };
    
    return JSON.stringify(config) !== JSON.stringify(originalConfig);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Edit Supplier Configuration
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {supplier.supplier_name} - {supplier.display_name}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleTestConnection}
              disabled={testing}
              className="inline-flex items-center px-3 py-1 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              <TestTube className={`w-4 h-4 mr-1 ${testing ? 'animate-pulse' : ''}`} />
              Test
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="space-y-6">
            {/* Success Message */}
            {successMessage && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
                <div className="flex">
                  <div className="w-5 h-5 text-green-400">✓</div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                      {successMessage}
                    </h3>
                  </div>
                </div>
              </div>
            )}

            {/* Error Display */}
            {errors.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <div className="flex">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                      Configuration Errors
                    </h3>
                    <ul className="mt-1 text-sm text-red-700 dark:text-red-300 list-disc list-inside">
                      {errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Test Result */}
            {testResult && (
              <div className={`border rounded-md p-4 ${
                testResult.success 
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
                  : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
              }`}>
                <div className="flex items-center">
                  <div className={`w-5 h-5 ${
                    testResult.success ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {testResult.success ? '✓' : '✗'}
                  </div>
                  <div className="ml-3">
                    <h3 className={`text-sm font-medium ${
                      testResult.success 
                        ? 'text-green-800 dark:text-green-200' 
                        : 'text-red-800 dark:text-red-200'
                    }`}>
                      Connection Test {testResult.success ? 'Successful' : 'Failed'}
                    </h3>
                    <p className={`mt-1 text-sm ${
                      testResult.success 
                        ? 'text-green-700 dark:text-green-300' 
                        : 'text-red-700 dark:text-red-300'
                    }`}>
                      {testResult.success 
                        ? `Connection established in ${testResult.test_duration_seconds.toFixed(2)}s`
                        : testResult.error_message
                      }
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Basic Information */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Basic Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Supplier Name
                  </label>
                  <input
                    type="text"
                    value={supplier.supplier_name}
                    readOnly
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Supplier name cannot be changed
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Display Name *
                  </label>
                  <input
                    type="text"
                    value={config.display_name}
                    onChange={(e) => handleConfigChange('display_name', e.target.value)}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    value={config.description}
                    onChange={(e) => handleConfigChange('description', e.target.value)}
                    rows={2}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={config.enabled}
                      onChange={(e) => handleConfigChange('enabled', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Enable this supplier configuration
                    </span>
                  </label>
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
                    onChange={(e) => handleConfigChange('base_url', e.target.value)}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    API Type
                  </label>
                  <select
                    value={config.api_type}
                    onChange={(e) => handleConfigChange('api_type', e.target.value)}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="rest">REST API</option>
                    <option value="graphql">GraphQL</option>
                    <option value="scraping">Web Scraping</option>
                  </select>
                </div>
                {config.api_type !== 'scraping' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      API Version
                    </label>
                    <input
                      type="text"
                      value={config.api_version}
                      onChange={(e) => handleConfigChange('api_version', e.target.value)}
                      placeholder="e.g., v1, v2, 2024-01"
                      className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      API version identifier (not needed for web scraping)
                    </p>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Rate Limit (per minute)
                  </label>
                  <input
                    type="number"
                    value={config.rate_limit_per_minute || ''}
                    onChange={(e) => handleConfigChange('rate_limit_per_minute', e.target.value ? parseInt(e.target.value) : null)}
                    min="1"
                    max={supplier.supplier_name === 'LCSC' ? "600" : "10000"}
                    placeholder={supplier.supplier_name === 'LCSC' ? "Recommended: 300 (5/sec)" : "Optional (leave empty for no limit)"}
                    className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {supplier.supplier_name === 'LCSC' 
                      ? '⚠️ LCSC uses web scraping - keep between 60-600 requests/minute (1-10 per second) to avoid being banned'
                      : 'Leave empty for no rate limiting, or enter 1-10000 requests per minute'
                    }
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Timeout (seconds)
                  </label>
                  <input
                    type="number"
                    value={config.timeout_seconds}
                    onChange={(e) => handleConfigChange('timeout_seconds', parseInt(e.target.value))}
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
                    onChange={(e) => handleConfigChange('max_retries', parseInt(e.target.value))}
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
                  const field = `supports_${capability.key.replace('fetch_', '')}` as keyof SupplierConfigUpdate;
                  const isEnabled = config[field] as boolean;
                  
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
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {errors.length > 0 ? (
              <span className="text-red-600 dark:text-red-400">
                ⚠️ Please fix validation errors above
              </span>
            ) : hasChanges() ? (
              'You have unsaved changes'
            ) : (
              'No changes made'
            )}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !hasChanges()}
              title={
                errors.length > 0
                  ? `Cannot save: ${errors.join(', ')}`
                  : !hasChanges()
                  ? "No changes to save"
                  : "Save the current configuration changes"
              }
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};