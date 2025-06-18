/**
 * Credentials Management Modal
 * 
 * Secure modal for managing encrypted supplier credentials with field masking and validation.
 */

import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Shield, Eye, EyeOff, Key, Save, Lock, HelpCircle } from 'lucide-react';
import { supplierService, SupplierCredentials } from '../../services/supplier.service';

interface CredentialsModalProps {
  supplierName: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface CredentialFieldDefinition {
  field: string;
  label: string;
  description?: string;
  type: 'text' | 'password';
  required: boolean;
  placeholder?: string;
  help_text?: string;
  validation?: {
    min_length?: number;
    max_length?: number;
    pattern?: string;
  };
}

export const CredentialsModal: React.FC<CredentialsModalProps> = ({ supplierName, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [hasExistingCredentials, setHasExistingCredentials] = useState(false);
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const [credentialFields, setCredentialFields] = useState<CredentialFieldDefinition[]>([]);
  
  const [credentials, setCredentials] = useState<SupplierCredentials>({
    api_key: '',
    secret_key: '',
    username: '',
    password: '',
    oauth_token: '',
    refresh_token: '',
    additional_data: {}
  });

  const [additionalFields, setAdditionalFields] = useState<Array<{ key: string; value: string }>>([]);

  useEffect(() => {
    loadSupplierInfo();
  }, [supplierName]);

  const loadSupplierInfo = async () => {
    try {
      setInitialLoading(true);
      
      // Load supplier info and credential field definitions in parallel
      const [supplier, fields] = await Promise.all([
        supplierService.getSupplier(supplierName),
        supplierService.getCredentialFields(supplierName)
      ]);
      
      setHasExistingCredentials(supplier.has_credentials);
      setCredentialFields(fields);
      
    } catch (err: any) {
      setErrors([err.response?.data?.detail || 'Failed to load supplier information']);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleCredentialChange = (field: keyof SupplierCredentials, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
    setErrors([]); // Clear errors when user makes changes
  };

  const handleAdditionalFieldChange = (index: number, key: string, value: string) => {
    const newFields = [...additionalFields];
    newFields[index] = { key, value };
    setAdditionalFields(newFields);
    
    // Update additional_data in credentials
    const newAdditionalData = { ...credentials.additional_data };
    newFields.forEach(field => {
      if (field.key.trim() && field.value.trim()) {
        newAdditionalData[field.key] = field.value;
      }
    });
    setCredentials(prev => ({ ...prev, additional_data: newAdditionalData }));
  };

  const addAdditionalField = () => {
    setAdditionalFields(prev => [...prev, { key: '', value: '' }]);
  };

  const removeAdditionalField = (index: number) => {
    const newFields = additionalFields.filter((_, i) => i !== index);
    setAdditionalFields(newFields);
    
    // Update additional_data
    const newAdditionalData: Record<string, string> = {};
    newFields.forEach(field => {
      if (field.key.trim() && field.value.trim()) {
        newAdditionalData[field.key] = field.value;
      }
    });
    setCredentials(prev => ({ ...prev, additional_data: newAdditionalData }));
  };

  const togglePasswordVisibility = (field: string) => {
    setShowPassword(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const validateCredentials = (): string[] => {
    const errors: string[] = [];
    
    // Validate dynamic credential fields
    credentialFields.forEach((fieldDef) => {
      const value = credentials[fieldDef.field as keyof SupplierCredentials] as string || '';
      
      // Check required fields
      if (fieldDef.required && !value.trim()) {
        errors.push(`${fieldDef.label} is required`);
        return;
      }
      
      if (value.trim() && fieldDef.validation) {
        // Check minimum length
        if (fieldDef.validation.min_length && value.length < fieldDef.validation.min_length) {
          errors.push(`${fieldDef.label} must be at least ${fieldDef.validation.min_length} characters`);
        }
        
        // Check maximum length
        if (fieldDef.validation.max_length && value.length > fieldDef.validation.max_length) {
          errors.push(`${fieldDef.label} must be no more than ${fieldDef.validation.max_length} characters`);
        }
        
        // Check pattern matching
        if (fieldDef.validation.pattern) {
          const regex = new RegExp(fieldDef.validation.pattern);
          if (!regex.test(value)) {
            errors.push(`${fieldDef.label} format is invalid`);
          }
        }
      }
    });
    
    // Check if at least one credential field is provided (for general validation)
    const hasAnyCredential = credentialFields.some(fieldDef => {
      const value = credentials[fieldDef.field as keyof SupplierCredentials] as string || '';
      return value.trim();
    }) || Object.keys(credentials.additional_data || {}).length > 0;
    
    if (!hasAnyCredential) {
      errors.push('At least one credential field must be provided');
    }

    // Validate additional fields
    additionalFields.forEach((field, index) => {
      if (field.key.trim() && !field.value.trim()) {
        errors.push(`Additional field "${field.key}" cannot have an empty value`);
      }
      if (!field.key.trim() && field.value.trim()) {
        errors.push(`Additional field at position ${index + 1} must have a key name`);
      }
    });

    return errors;
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setErrors([]);

      // Validate credentials
      const validationErrors = validateCredentials();
      if (validationErrors.length > 0) {
        setErrors(validationErrors);
        return;
      }

      // Filter out empty credentials
      const filteredCredentials: SupplierCredentials = {};
      Object.entries(credentials).forEach(([key, value]) => {
        if (key === 'additional_data') {
          if (value && Object.keys(value).length > 0) {
            filteredCredentials[key as keyof SupplierCredentials] = value as any;
          }
        } else if (value && value.trim()) {
          filteredCredentials[key as keyof SupplierCredentials] = value as any;
        }
      });

      // Store or update credentials
      if (hasExistingCredentials) {
        await supplierService.updateCredentials(supplierName, filteredCredentials);
      } else {
        await supplierService.storeCredentials(supplierName, filteredCredentials);
      }

      onSuccess();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to save credentials';
      setErrors([errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCredentials = async () => {
    if (!confirm('Are you sure you want to delete all credentials for this supplier? This action cannot be undone.')) {
      return;
    }

    try {
      setLoading(true);
      await supplierService.deleteCredentials(supplierName);
      onSuccess();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to delete credentials';
      setErrors([errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const hasAnyCredentials = () => {
    return Object.entries(credentials).some(([key, value]) => {
      if (key === 'additional_data') {
        return Object.keys(value || {}).length > 0;
      }
      return value && value.trim();
    }) || additionalFields.some(field => field.key.trim() || field.value.trim());
  };

  if (initialLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Manage Credentials
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {supplierName} - {hasExistingCredentials ? 'Update existing credentials' : 'Set up new credentials'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="space-y-6">
            {/* Security Notice */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
              <div className="flex">
                <Lock className="w-5 h-5 text-blue-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    Security Notice
                  </h3>
                  <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                    All credentials are encrypted using AES-256-GCM encryption before being stored. 
                    Your sensitive data is protected at rest and only decrypted when needed for API operations.
                  </p>
                </div>
              </div>
            </div>

            {/* Error Display */}
            {errors.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <div className="flex">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                      Validation Errors
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

            {/* Dynamic Credential Fields */}
            {credentialFields.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                  <Key className="w-5 h-5 mr-2" />
                  Credentials
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {credentialFields.map((fieldDef) => (
                    <div key={fieldDef.field} className="space-y-2">
                      <div className="flex items-center space-x-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          {fieldDef.label}
                          {fieldDef.required && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        {fieldDef.help_text && (
                          <div className="group relative">
                            <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 pointer-events-none">
                              {fieldDef.help_text}
                              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                            </div>
                          </div>
                        )}
                      </div>
                      {fieldDef.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {fieldDef.description}
                        </p>
                      )}
                      <div className="relative">
                        <input
                          type={fieldDef.type === 'password' && !showPassword[fieldDef.field] ? 'password' : 'text'}
                          value={(credentials[fieldDef.field as keyof SupplierCredentials] as string) || ''}
                          onChange={(e) => handleCredentialChange(fieldDef.field as keyof SupplierCredentials, e.target.value)}
                          placeholder={fieldDef.placeholder}
                          className={`w-full border rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
                            fieldDef.type === 'password' ? 'pr-10' : ''
                          } ${
                            fieldDef.required 
                              ? 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500' 
                              : 'border-gray-200 dark:border-gray-700'
                          }`}
                          required={fieldDef.required}
                        />
                        {fieldDef.type === 'password' && (
                          <button
                            type="button"
                            onClick={() => togglePasswordVisibility(fieldDef.field)}
                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          >
                            {showPassword[fieldDef.field] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Additional Fields */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Additional Fields
                </h3>
                <button
                  onClick={addAdditionalField}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
                >
                  Add Field
                </button>
              </div>
              <div className="space-y-3">
                {additionalFields.map((field, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={field.key}
                      onChange={(e) => handleAdditionalFieldChange(index, e.target.value, field.value)}
                      placeholder="Field name"
                      className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                    <div className="relative flex-1">
                      <input
                        type={showPassword[`additional_${index}`] ? 'text' : 'password'}
                        value={field.value}
                        onChange={(e) => handleAdditionalFieldChange(index, field.key, e.target.value)}
                        placeholder="Field value"
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 pr-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility(`additional_${index}`)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        {showPassword[`additional_${index}`] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <button
                      onClick={() => removeAdditionalField(index)}
                      className="text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {additionalFields.length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                    No additional fields configured
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div>
            {hasExistingCredentials && (
              <button
                onClick={handleDeleteCredentials}
                disabled={loading}
                className="text-sm text-red-600 dark:text-red-400 hover:text-red-500 dark:hover:text-red-300 disabled:opacity-50"
              >
                Delete All Credentials
              </button>
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
              disabled={loading || !hasAnyCredentials()}
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
                  {hasExistingCredentials ? 'Update Credentials' : 'Save Credentials'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};