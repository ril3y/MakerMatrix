/**
 * Reusable Credential Editor Component
 * 
 * Provides a consistent interface for editing supplier credentials across all suppliers.
 * Shows masked current values, allows editing, and includes test functionality.
 */

import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, TestTube, Save, HelpCircle, CheckCircle, XCircle } from 'lucide-react';

interface CredentialField {
  name: string;
  label: string;
  field_type: string;
  required: boolean;
  description?: string;
  placeholder?: string;
  help_text?: string;
}

interface CredentialEditorProps {
  supplierName: string;
  credentialSchema: CredentialField[];
  currentlyConfigured?: boolean; // Whether credentials are already set on backend
  credentialStatus?: any; // Full credential status from backend
  onCredentialChange?: (credentials: Record<string, string>) => void;
  onTest?: (credentials: Record<string, string>) => Promise<{ success: boolean; message?: string }>;
  onSave?: (credentials: Record<string, string>) => Promise<void>;
  loading?: boolean;
  onCredentialsReady?: (credentials: Record<string, string>) => void; // Expose current credentials
}

export const CredentialEditor: React.FC<CredentialEditorProps> = ({
  supplierName,
  credentialSchema,
  currentlyConfigured = false,
  credentialStatus,
  onCredentialChange,
  onTest,
  onSave,
  loading = false,
  onCredentialsReady
}) => {
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message?: string } | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize credentials when schema changes or credential status loads
  useEffect(() => {
    if (credentialSchema.length === 0) return;
    
    const initializeCredentials = async () => {
      const initialCredentials: Record<string, string> = {};
      const initialShowValues: Record<string, boolean> = {};
      
      // Fetch actual credentials if any are configured
      let actualCredentials: Record<string, string> = {};
      if (credentialStatus && (credentialStatus.has_database_credentials || credentialStatus.has_environment_credentials)) {
        try {
          const apiUrl = `/api/suppliers/${supplierName.toLowerCase()}/credentials`;
          console.log('Fetching credentials for:', supplierName);
          console.log('API URL:', apiUrl);
          const response = await fetch(apiUrl, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
          });
          console.log('Credentials API response status:', response.status);
          if (response.ok) {
            const data = await response.json();
            console.log('Credentials API response data:', JSON.stringify(data, null, 2));
            console.log('data.data:', JSON.stringify(data.data, null, 2));
            console.log('Object.keys(data.data):', Object.keys(data.data || {}));
            actualCredentials = data.data || data || {};
            console.log('Extracted actualCredentials:', JSON.stringify(actualCredentials, null, 2));
          } else {
            console.error('Credentials API failed:', response.status, response.statusText);
          }
        } catch (error) {
          console.error('Failed to fetch credentials:', error);
        }
      } else {
        console.log('No credentials configured, credentialStatus:', credentialStatus);
      }
      
      credentialSchema.forEach(field => {
        // Use actual value if available, otherwise empty string
        const actualValue = actualCredentials[field.name];
        initialCredentials[field.name] = actualValue || '';
        
        // Password fields start hidden, text fields start visible
        initialShowValues[field.name] = field.field_type !== 'password';
      });
      
      setCredentials(initialCredentials);
      setShowValues(initialShowValues);
      setHasChanges(false);
    };
    
    initializeCredentials();
  }, [credentialSchema, credentialStatus, supplierName]);

  // Separate effect to notify parent of credentials (only when credentials actually change)
  useEffect(() => {
    if (onCredentialsReady && Object.keys(credentials).length > 0) {
      onCredentialsReady(credentials);
    }
  }, [credentials, onCredentialsReady]);

  const handleFieldChange = (fieldName: string, value: string) => {
    const updatedCredentials = { ...credentials, [fieldName]: value };
    setCredentials(updatedCredentials);
    setHasChanges(true);
    
    if (onCredentialChange) {
      onCredentialChange(updatedCredentials);
    }
    
    if (onCredentialsReady) {
      onCredentialsReady(updatedCredentials);
    }
  };

  const toggleShowValue = (fieldName: string) => {
    setShowValues(prev => ({ ...prev, [fieldName]: !prev[fieldName] }));
  };

  const handleTest = async () => {
    if (!onTest) return;
    
    try {
      setTesting(true);
      setTestResult(null);
      const result = await onTest(credentials);
      setTestResult(result);
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: error instanceof Error ? error.message : 'Test failed' 
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (!onSave) return;
    
    try {
      setSaving(true);
      await onSave(credentials);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save credentials:', error);
    } finally {
      setSaving(false);
    }
  };

  const getConfiguredStatus = (): boolean => {
    if (!credentialStatus) return false;
    return credentialStatus.fully_configured || false;
  };

  const getStatusText = (): string => {
    if (!credentialStatus) return 'Loading...';
    
    if (credentialStatus.error) {
      return 'Error Loading Status';
    }
    
    const hasDb = credentialStatus.has_database_credentials;
    const hasEnv = credentialStatus.has_environment_credentials;
    const isConfigured = credentialStatus.fully_configured;
    
    if (isConfigured) {
      if (hasDb && hasEnv) {
        return 'Credentials Set (DB + Environment)';
      } else if (hasDb) {
        return 'Credentials Set (Database)';
      } else if (hasEnv) {
        return 'Credentials Set (Environment)';
      } else {
        return 'Configured';
      }
    } else {
      const missing = credentialStatus.missing_required?.length || 0;
      return missing > 0 ? `Missing ${missing} Required Field${missing > 1 ? 's' : ''}` : 'No Credentials Set';
    }
  };

  if (credentialSchema.length === 0) {
    return (
      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
        <div className="flex items-center">
          <div className="w-5 h-5 text-green-400">✓</div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-green-800 dark:text-green-200">
              No Credentials Required
            </h4>
            <p className="text-sm text-green-700 dark:text-green-300 mt-1">
              This supplier uses public APIs or web scraping and doesn't require authentication credentials.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Compact Status Header */}
      <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
        <div className="flex items-center space-x-2">
          {getConfiguredStatus() ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
          <span className="text-sm font-medium">
            {getStatusText()}
          </span>
        </div>
        <span className="text-xs text-gray-500">
          {getConfiguredStatus() ? 'Enter new values to update' : 'Required for API access'}
        </span>
      </div>
      

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
                Credentials Test {testResult.success ? 'Successful' : 'Failed'}
              </h3>
              {testResult.message && (
                <p className={`mt-1 text-sm ${
                  testResult.success 
                    ? 'text-green-700 dark:text-green-300' 
                    : 'text-red-700 dark:text-red-300'
                }`}>
                  {testResult.message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Credential Fields - Compact */}
      <div className="space-y-3">
        {credentialSchema.map((field) => {
          const isPassword = field.field_type === 'password';
          const currentValue = credentials[field.name] || '';
          const isConfigured = credentialStatus?.configured_fields?.includes(field.name) || false;
          const shouldShow = showValues[field.name];
          const hasValue = currentValue.length > 0;
          
          return (
            <div key={field.name} className="space-y-1">
              <div className="flex items-center space-x-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                
                {/* Status Indicator */}
                <div className="flex items-center space-x-1">
                  {isConfigured ? (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200">
                      SET
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200">
                      REQUIRED
                    </span>
                  )}
                  
                  {/* Help Tooltip */}
                  {(field.description || field.help_text) && (
                    <div className="group relative">
                      <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                        {field.description && <div className="font-medium">{field.description}</div>}
                        {field.help_text && <div className="mt-1 text-gray-300">{field.help_text}</div>}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="relative">
                <input
                  type={shouldShow ? 'text' : 'password'}
                  value={currentValue}
                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  placeholder={`Enter ${field.label.toLowerCase()}`}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white pr-10"
                  disabled={loading}
                />
                
                {(isPassword || hasValue) && (
                  <button
                    type="button"
                    onClick={() => toggleShowValue(field.name)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    title="Toggle visibility"
                  >
                    {shouldShow ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Buttons */}
      {onSave && (
        <div className="flex items-center space-x-3 pt-4">
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving || loading}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className={`w-4 h-4 mr-2 ${saving ? 'animate-pulse' : ''}`} />
            {saving ? 'Saving...' : 'Save Credentials'}
          </button>
        </div>
      )}

    </div>
  );
};