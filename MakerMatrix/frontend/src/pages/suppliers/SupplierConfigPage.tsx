/**
 * Supplier Configuration Management Page
 * 
 * Provides a comprehensive interface for managing supplier API configurations,
 * credentials, and enrichment capabilities with security features.
 */

import React, { useState, useEffect } from 'react';
import { Plus, Settings, TestTube, Upload, RefreshCw, AlertTriangle, CheckCircle, XCircle, Eye, EyeOff } from 'lucide-react';
import { supplierService, SupplierConfig, ConnectionTestResult } from '../../services/supplier.service';
import { DynamicAddSupplierModal } from './DynamicAddSupplierModal';
import { EditSupplierModal } from './EditSupplierModal';
import { ImportExportModal } from './ImportExportModal';

export const SupplierConfigPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<SupplierConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<SupplierConfig | null>(null);
  const [showImportExport, setShowImportExport] = useState(false);
  
  // UI states
  const [showCredentialStatus, setShowCredentialStatus] = useState(false);

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await supplierService.getSuppliers();
      setSuppliers(data || []);
    } catch (err: any) {
      console.error('Error loading suppliers:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load supplier configurations';
      setError(errorMessage);
      setSuppliers([]); // Ensure suppliers is always an array
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (supplierName: string) => {
    try {
      setTesting(prev => ({ ...prev, [supplierName]: true }));
      console.log(`Testing connection for supplier: ${supplierName}`);
      const result = await supplierService.testConnection(supplierName);
      console.log(`Test result for ${supplierName}:`, result);
      setTestResults(prev => ({ ...prev, [supplierName]: result }));
    } catch (err: any) {
      console.error(`Test failed for ${supplierName}:`, err);
      setTestResults(prev => ({ 
        ...prev, 
        [supplierName]: {
          supplier_name: supplierName,
          success: false,
          test_duration_seconds: 0,
          tested_at: new Date().toISOString(),
          error_message: err.response?.data?.detail || 'Connection test failed'
        }
      }));
    } finally {
      setTesting(prev => ({ ...prev, [supplierName]: false }));
    }
  };

  const handleToggleEnabled = async (supplier: SupplierConfig) => {
    try {
      await supplierService.updateSupplier(supplier.supplier_name, {
        enabled: !supplier.enabled
      });
      await loadSuppliers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update supplier status');
    }
  };

  const handleDeleteSupplier = async (supplierName: string) => {
    if (!confirm(`Are you sure you want to delete the supplier configuration for "${supplierName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await supplierService.deleteSupplier(supplierName);
      await loadSuppliers();
      // Clear test results for deleted supplier
      setTestResults(prev => {
        const newResults = { ...prev };
        delete newResults[supplierName];
        return newResults;
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete supplier configuration');
    }
  };


  // Use all suppliers without filtering
  const filteredSuppliers = suppliers || [];

  const getStatusIcon = (supplier: SupplierConfig) => {
    if (!supplier.enabled) {
      return <XCircle className="w-5 h-5 text-gray-400" />;
    }

    const testResult = testResults[supplier.supplier_name];
    if (!testResult) {
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    }

    return testResult.success ? 
      <CheckCircle className="w-5 h-5 text-green-500" /> : 
      <XCircle className="w-5 h-5 text-red-500" />;
  };

  const getStatusText = (supplier: SupplierConfig) => {
    if (!supplier.enabled) return 'Disabled';
    
    const testResult = testResults[supplier.supplier_name];
    if (!testResult) return 'Not tested';
    
    return testResult.success ? 'Connected' : 'Connection failed';
  };

  if (loading && suppliers.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Supplier Configuration
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-300">
                Manage supplier API configurations, credentials, and enrichment capabilities
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowImportExport(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                <Upload className="w-4 h-4 mr-2" />
                Import/Export
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Supplier
              </button>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
            <div className="flex">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Header Info */}
        <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowCredentialStatus(!showCredentialStatus)}
                className="inline-flex items-center px-3 py-1 border border-gray-300 dark:border-gray-600 text-sm rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                {showCredentialStatus ? <EyeOff className="w-4 h-4 mr-1" /> : <Eye className="w-4 h-4 mr-1" />}
                Show Credentials Status
              </button>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {filteredSuppliers.length} supplier{filteredSuppliers.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>


        {/* Suppliers Grid */}
        {filteredSuppliers.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
            <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No suppliers found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              Get started by adding your first supplier configuration or initializing defaults.
            </p>
            {(suppliers || []).length === 0 && (
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => setShowAddModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Supplier
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredSuppliers.map((supplier) => (
              <div
                key={supplier.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700"
              >
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(supplier)}
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                          {supplier.display_name}
                        </h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {supplier.supplier_name}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleTestConnection(supplier.supplier_name)}
                        disabled={testing[supplier.supplier_name]}
                        className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50"
                        title="Test Connection"
                      >
                        <TestTube className={`w-4 h-4 ${testing[supplier.supplier_name] ? 'animate-pulse' : ''}`} />
                      </button>
                      <button
                        onClick={() => setEditingSupplier(supplier)}
                        className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        title="Edit Configuration"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Description */}
                  {supplier.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
                      {supplier.description}
                    </p>
                  )}

                  {/* Status and Info */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500 dark:text-gray-400">Status:</span>
                      <span className={`text-sm font-medium ${
                        supplier.enabled ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      }`}>
                        {getStatusText(supplier)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500 dark:text-gray-400">API Type:</span>
                      <span className="text-sm text-gray-900 dark:text-white uppercase">
                        {supplier.api_type}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500 dark:text-gray-400">Capabilities:</span>
                      <span className="text-sm text-gray-900 dark:text-white">
                        {supplier.capabilities.length}
                      </span>
                    </div>

                    {showCredentialStatus && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">Credentials:</span>
                        <span className={`text-sm font-medium ${
                          supplier.has_credentials ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'
                        }`}>
                          {supplier.has_credentials ? 'Configured' : 'Not Set'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Capabilities */}
                  <div className="mt-4">
                    <div className="flex flex-wrap gap-1">
                      {supplier.capabilities.map((capability) => (
                        <span
                          key={capability}
                          className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200"
                        >
                          {capability.replace('fetch_', '').replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Test Results */}
                  {testResults[supplier.supplier_name] && (
                    <div className={`mt-4 p-3 border rounded-md ${
                      testResults[supplier.supplier_name].success 
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                    }`}>
                      <div className="flex">
                        {testResults[supplier.supplier_name].success ? (
                          <CheckCircle className="w-4 h-4 text-green-400 mt-0.5" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400 mt-0.5" />
                        )}
                        <div className="ml-2">
                          <h4 className={`text-sm font-medium ${
                            testResults[supplier.supplier_name].success 
                              ? 'text-green-800 dark:text-green-200'
                              : 'text-red-800 dark:text-red-200'
                          }`}>
                            Connection Test {testResults[supplier.supplier_name].success ? 'Successful' : 'Failed'}
                          </h4>
                          <p className={`text-sm mt-1 ${
                            testResults[supplier.supplier_name].success 
                              ? 'text-green-700 dark:text-green-300'
                              : 'text-red-700 dark:text-red-300'
                          }`}>
                            {testResults[supplier.supplier_name].success 
                              ? `Connected successfully in ${testResults[supplier.supplier_name].test_duration_seconds.toFixed(2)}s`
                              : (testResults[supplier.supplier_name].error_message || 'Unknown error occurred')
                            }
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-6 flex items-center justify-end">
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => handleToggleEnabled(supplier)}
                        className={`text-sm font-medium ${
                          supplier.enabled 
                            ? 'text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300' 
                            : 'text-green-600 dark:text-green-400 hover:text-green-500 dark:hover:text-green-300'
                        }`}
                      >
                        {supplier.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => handleDeleteSupplier(supplier.supplier_name)}
                        className="text-sm text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modals */}
        {showAddModal && (
          <DynamicAddSupplierModal
            onClose={() => setShowAddModal(false)}
            onSuccess={() => {
              setShowAddModal(false);
              loadSuppliers();
            }}
          />
        )}

        {editingSupplier && (
          <EditSupplierModal
            supplier={editingSupplier}
            onClose={() => setEditingSupplier(null)}
            onSuccess={() => {
              setEditingSupplier(null);
              loadSuppliers();
            }}
          />
        )}


        {showImportExport && (
          <ImportExportModal
            onClose={() => setShowImportExport(false)}
            onSuccess={() => {
              setShowImportExport(false);
              loadSuppliers();
            }}
          />
        )}
      </div>
    </div>
  );
};