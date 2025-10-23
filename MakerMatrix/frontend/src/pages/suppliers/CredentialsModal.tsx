/**
 * Environment Variables Guide Modal
 *
 * Simple modal explaining how to configure supplier credentials via environment variables.
 */

import React from 'react'
import { X, Shield, AlertCircle, ExternalLink } from 'lucide-react'

interface CredentialsModalProps {
  supplierName: string
  onClose: () => void
  onSuccess: () => void
}

export const CredentialsModal: React.FC<CredentialsModalProps> = ({ supplierName, onClose }) => {
  const getEnvironmentVariables = (supplier: string) => {
    const upperSupplier = supplier.toUpperCase()
    switch (upperSupplier) {
      case 'LCSC':
        return []
      case 'DIGIKEY':
        return ['DIGIKEY_API_KEY', 'DIGIKEY_SECRET_KEY']
      case 'MOUSER':
        return ['MOUSER_API_KEY']
      default:
        return [`${upperSupplier}_API_KEY`]
    }
  }

  const envVars = getEnvironmentVariables(supplierName)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Environment Variables Setup
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {supplierName} credentials are now configured via environment variables
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
            {/* Info Notice */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
              <div className="flex">
                <AlertCircle className="w-5 h-5 text-blue-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    Credential Storage Change
                  </h3>
                  <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                    For improved security, supplier credentials are no longer stored in the
                    database. Instead, set them as environment variables on the server where
                    MakerMatrix is running.
                  </p>
                </div>
              </div>
            </div>

            {/* Environment Variables */}
            {envVars.length > 0 ? (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Required Environment Variables for {supplierName}
                </h3>
                <div className="space-y-3">
                  {envVars.map((envVar) => (
                    <div
                      key={envVar}
                      className="bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600 p-3"
                    >
                      <code className="text-sm font-mono text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                        {envVar}=your_api_key_here
                      </code>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md p-4">
                <div className="flex">
                  <Shield className="w-5 h-5 text-green-400" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">
                      No Credentials Required
                    </h3>
                    <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                      {supplierName} uses a public API and does not require authentication
                      credentials.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Setup Instructions */}
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Setup Instructions
              </h3>
              <div className="space-y-4 text-sm text-gray-600 dark:text-gray-300">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    1. Obtain API Credentials
                  </h4>
                  <p>
                    Visit the {supplierName} developer portal or account settings to generate API
                    keys.
                  </p>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    2. Set Environment Variables
                  </h4>
                  <p className="mb-2">Add the environment variables to your system:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>
                      <strong>Linux/macOS:</strong> Add to ~/.bashrc or ~/.zshrc
                    </li>
                    <li>
                      <strong>Docker:</strong> Add to docker-compose.yml or Dockerfile
                    </li>
                    <li>
                      <strong>Systemd:</strong> Add to service file Environment section
                    </li>
                  </ul>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    3. Restart MakerMatrix
                  </h4>
                  <p>
                    Restart the MakerMatrix backend service to load the new environment variables.
                  </p>
                </div>
              </div>
            </div>

            {/* Example */}
            {envVars.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Example (.env file)
                </h3>
                <pre className="bg-gray-800 text-green-400 p-3 rounded text-sm overflow-x-auto">
                  {envVars.map((envVar) => `${envVar}=your_actual_api_key_here`).join('\n')}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <a
            href="https://github.com/your-repo/makermatrix/wiki/Environment-Variables"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300"
          >
            <ExternalLink className="w-4 h-4 mr-1" />
            View Documentation
          </a>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
