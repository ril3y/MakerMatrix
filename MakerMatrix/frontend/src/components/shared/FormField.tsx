/**
 * Reusable Form Field Component
 * 
 * Renders a form field based on a field definition schema, handling different input types.
 */

import React from 'react';

interface FieldDefinition {
  name: string;
  label: string;
  field_type: string;
  required?: boolean;
  description?: string;
  placeholder?: string;
  help_text?: string;
  options?: Array<{ value: string; label: string }>;
  validation?: Record<string, any>;
}

interface FormFieldProps {
  field: FieldDefinition;
  value: any;
  onChange: (value: any) => void;
  disabled?: boolean;
}

export const FormField: React.FC<FormFieldProps> = ({ field, value, onChange, disabled }) => {
  const fieldId = `field-${field.name}`;

  const renderField = () => {
    switch (field.field_type) {
      case 'password':
        return (
          <input
            id={fieldId}
            type="password"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          />
        );

      case 'email':
        return (
          <input
            id={fieldId}
            type="email"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          />
        );

      case 'url':
        return (
          <input
            id={fieldId}
            type="url"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          />
        );

      case 'number':
        return (
          <input
            id={fieldId}
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            min={field.validation?.min}
            max={field.validation?.max}
            disabled={disabled}
          />
        );

      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <input
              id={fieldId}
              type="checkbox"
              checked={!!value}
              onChange={(e) => onChange(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={disabled}
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {field.description || 'Enable this option'}
            </span>
          </label>
        );

      case 'select':
        return (
          <select
            id={fieldId}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          >
            <option value="">Select...</option>
            {field.options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'textarea':
        return (
          <textarea
            id={fieldId}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            rows={3}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          />
        );

      default:
        return (
          <input
            id={fieldId}
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            required={field.required}
            disabled={disabled}
          />
        );
    }
  };

  return (
    <div>
      <label htmlFor={fieldId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {field.label} {field.required && <span className="text-red-500">*</span>}
      </label>
      {renderField()}
      {field.help_text && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {field.help_text}
        </p>
      )}
    </div>
  );
};
