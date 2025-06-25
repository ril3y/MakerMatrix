import React from 'react';
import { Plus } from 'lucide-react';
import { Category } from '../../types/categories';
import FormField from './FormField';

interface CategorySelectorProps {
  categories: Category[];
  selectedCategories: string[];
  onToggleCategory: (categoryId: string) => void;
  onAddNewCategory?: () => void;
  label?: string;
  description?: string;
  error?: string;
  showAddButton?: boolean;
  layout?: 'checkboxes' | 'pills';
  className?: string;
}

const CategorySelector: React.FC<CategorySelectorProps> = ({
  categories,
  selectedCategories,
  onToggleCategory,
  onAddNewCategory,
  label = "Categories",
  description,
  error,
  showAddButton = false,
  layout = 'checkboxes',
  className = ''
}) => {
  if (layout === 'pills') {
    return (
      <div className={className}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary">{label}</h2>
          {showAddButton && onAddNewCategory && (
            <button
              type="button"
              onClick={onAddNewCategory}
              className="btn btn-secondary text-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add New Category
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <button
              key={category.id}
              type="button"
              onClick={() => onToggleCategory(category.id)}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                selectedCategories.includes(category.id)
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {category.name}
            </button>
          ))}
          {categories.length === 0 && (
            <p className="text-muted text-sm">No categories available. Create your first category above.</p>
          )}
        </div>
      </div>
    );
  }

  // Checkboxes layout (similar to AddPartModal)
  return (
    <FormField 
      label={label} 
      description={description}
      error={error}
      className={className}
    >
      <div className="space-y-3">
        {showAddButton && onAddNewCategory && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onAddNewCategory}
              className="btn btn-secondary btn-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add New Category
            </button>
          </div>
        )}
        
        <div className="border border-border rounded-md p-3 max-h-32 overflow-y-auto">
          {categories.length > 0 ? (
            <div className="space-y-2">
              {categories.map((category) => (
                <label key={category.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category.id)}
                    onChange={() => onToggleCategory(category.id)}
                    className="rounded border-border"
                  />
                  <span className="text-sm text-primary">{category.name}</span>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-sm text-secondary">No categories available</p>
          )}
        </div>
      </div>
    </FormField>
  );
};

export default CategorySelector;