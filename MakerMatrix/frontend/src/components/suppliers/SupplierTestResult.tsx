/**
 * Supplier Test Result Component
 * 
 * Reusable component for displaying supplier connection test results
 * with proper OAuth handling, instructions, and error messages.
 * Used by both Add and Edit supplier modals.
 */

import React from 'react';
import { CheckCircle, AlertTriangle, HelpCircle } from 'lucide-react';

export interface SupplierTestResultData {
  success: boolean;
  message: string;
  error_message?: string;
  test_duration_seconds?: number;
  details?: {
    oauth_required?: boolean;
    oauth_url?: string;
    environment?: string;
    instructions?: string;
    configuration_needed?: boolean;
    missing_credentials?: string[];
    setup_url?: string;
    install_command?: string;
    api_reachable?: boolean;
    credentials_valid?: boolean;
    [key: string]: any;
  };
}

interface SupplierTestResultProps {
  testResult: SupplierTestResultData;
  className?: string;
}

export const SupplierTestResult: React.FC<SupplierTestResultProps> = ({ 
  testResult, 
  className = "" 
}) => {
  // Debug logging to see what the frontend is receiving
  console.log('SupplierTestResult received:', testResult);
  
  return (
    <div className={`border rounded-md p-3 ${
      testResult.success 
        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
        : testResult.details?.configuration_needed || testResult.details?.oauth_required
        ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
    } ${className}`}>
      <div className="flex">
        {testResult.success ? (
          <CheckCircle className="w-5 h-5 text-green-400" />
        ) : testResult.details?.oauth_required ? (
          <HelpCircle className="w-5 h-5 text-yellow-400" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-red-400" />
        )}
        <div className="ml-3 flex-1">
          <p className={`text-sm font-medium ${
            testResult.success 
              ? 'text-green-800 dark:text-green-200' 
              : testResult.details?.configuration_needed || testResult.details?.oauth_required
              ? 'text-yellow-800 dark:text-yellow-200'
              : 'text-red-800 dark:text-red-200'
          }`}>
            {testResult.success 
              ? `Connection established in ${testResult.test_duration_seconds?.toFixed(2) || '0'}s`
              : testResult.message || testResult.error_message
            }
          </p>
          
          {/* Enhanced details */}
          {!testResult.success && testResult.details && (
            <div className="mt-3 space-y-2">
              {/* Configuration needed */}
              {testResult.details.configuration_needed && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3">
                  <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
                    Configuration Required
                  </h4>
                  {testResult.details.missing_credentials && (
                    <p className="text-xs text-blue-700 dark:text-blue-300 mb-2">
                      Missing: {testResult.details.missing_credentials.join(', ')}
                    </p>
                  )}
                  {testResult.details.setup_url && (
                    <a 
                      href={testResult.details.setup_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-xs text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
                    >
                      Get credentials at {testResult.details.setup_url} →
                    </a>
                  )}
                </div>
              )}
              
              {/* OAuth required */}
              {testResult.details.oauth_required && testResult.details.oauth_url && (
                <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded p-3">
                  <h4 className="text-sm font-medium text-purple-800 dark:text-purple-200 mb-1">
                    OAuth Authentication Required
                  </h4>
                  <p className="text-xs text-purple-700 dark:text-purple-300 mb-2">
                    {testResult.details.environment === 'headless' 
                      ? 'Running in headless environment - manual OAuth needed'
                      : 'Complete OAuth authentication to test API connection'
                    }
                  </p>
                  <a 
                    href={testResult.details.oauth_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-xs bg-purple-100 dark:bg-purple-800 text-purple-800 dark:text-purple-200 px-2 py-1 rounded hover:bg-purple-200 dark:hover:bg-purple-700"
                  >
                    Complete OAuth Authentication →
                  </a>
                </div>
              )}
              
              {/* Instructions */}
              {testResult.details.instructions && (
                <div className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded p-3">
                  <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
                    Instructions
                  </h4>
                  <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                    {testResult.details.instructions}
                  </pre>
                </div>
              )}
              
              {/* Install command for missing dependencies */}
              {testResult.details.install_command && (
                <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded p-3">
                  <h4 className="text-sm font-medium text-orange-800 dark:text-orange-200 mb-1">
                    Missing Dependency
                  </h4>
                  <code className="text-xs bg-orange-100 dark:bg-orange-800 text-orange-800 dark:text-orange-200 px-2 py-1 rounded">
                    {testResult.details.install_command}
                  </code>
                </div>
              )}
              
              {/* Fallback: Show other details as JSON only if not OAuth/config related */}
              {!testResult.details.oauth_required && 
               !testResult.details.configuration_needed && 
               !testResult.details.instructions && 
               !testResult.details.install_command && (
                <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-2 rounded">
                  {JSON.stringify(testResult.details, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};