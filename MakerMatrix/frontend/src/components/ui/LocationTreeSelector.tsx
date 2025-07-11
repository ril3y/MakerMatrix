import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, MapPin, Plus } from 'lucide-react';
import { Location } from '../../types/locations';
import { locationsService } from '../../services/locations.service';
import FormField from './FormField';

interface LocationTreeSelectorProps {
  selectedLocationId?: string;
  onLocationSelect: (locationId: string | undefined) => void;
  onAddNewLocation?: () => void;
  label?: string;
  description?: string;
  error?: string;
  showAddButton?: boolean;
  className?: string;
  compact?: boolean; // For modal use
}

interface LocationTreeNodeProps {
  locations: Location[];
  selectedLocationId?: string;
  expandedNodes: Set<string>;
  toggleExpanded: (id: string) => void;
  onLocationSelect: (locationId: string | undefined) => void;
  level?: number;
  compact?: boolean;
}

const LocationTreeNode: React.FC<LocationTreeNodeProps> = ({ 
  locations, 
  selectedLocationId,
  expandedNodes, 
  toggleExpanded, 
  onLocationSelect,
  level = 0,
  compact = false
}) => {
  return (
    <div className="space-y-1">
      {locations.map((location) => {
        const hasChildren = location.children && location.children.length > 0;
        const isExpanded = expandedNodes.has(location.id.toString());
        const isSelected = selectedLocationId === location.id;

        return (
          <div key={location.id}>
            <div 
              className={`flex items-start gap-2 p-2 rounded hover:bg-theme-secondary transition-colors cursor-pointer min-w-0 ${
                isSelected ? 'bg-primary-10 border border-primary-20' : ''
              }`}
              style={{ paddingLeft: `${level * (compact ? 16 : 24) + 8}px` }}
              onClick={() => onLocationSelect(isSelected ? undefined : location.id)}
            >
              <div className="flex items-center gap-2 flex-1">
                {hasChildren ? (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpanded(location.id.toString());
                    }}
                    className="p-1 hover:bg-theme-tertiary rounded transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} text-theme-secondary`} />
                    ) : (
                      <ChevronRight className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} text-theme-secondary`} />
                    )}
                  </button>
                ) : (
                  <div className={compact ? "w-5" : "w-6"} />
                )}
                
                <div className="flex items-center gap-2">
                  {location.emoji ? (
                    <span className={compact ? "text-sm" : "text-base"}>{location.emoji}</span>
                  ) : location.image_url ? (
                    <img
                      src={location.image_url}
                      alt={location.name}
                      className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} object-cover rounded border border-theme-primary`}
                    />
                  ) : (
                    <MapPin className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} text-primary-accent`} />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`font-medium text-theme-primary ${compact ? 'text-sm' : 'text-base'} truncate`}>
                      {location.name}
                    </span>
                    
                    {!compact && (
                      <span className="text-sm text-theme-secondary whitespace-nowrap">
                        ({location.location_type || 'General'})
                      </span>
                    )}
                  </div>
                  
                  {!compact && location.description && (
                    <div className="text-sm text-theme-muted mt-1 line-clamp-2">
                      {location.description}
                    </div>
                  )}
                </div>
              </div>
              
              {isSelected && (
                <div className="w-2 h-2 bg-primary rounded-full" />
              )}
            </div>
            
            {hasChildren && isExpanded && (
              <LocationTreeNode
                locations={location.children!}
                selectedLocationId={selectedLocationId}
                expandedNodes={expandedNodes}
                toggleExpanded={toggleExpanded}
                onLocationSelect={onLocationSelect}
                level={level + 1}
                compact={compact}
              />
            )}
          </div>
        );
      })}
    </div>
  );
};

const LocationTreeSelector: React.FC<LocationTreeSelectorProps> = ({
  selectedLocationId,
  onLocationSelect,
  onAddNewLocation,
  label = "Location",
  description,
  error,
  showAddButton = false,
  className = '',
  compact = false
}) => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [locationTree, setLocationTree] = useState<Location[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadLocations = async () => {
      try {
        setLoading(true);
        const data = await locationsService.getAllLocations();
        setLocations(data);
        const tree = locationsService.buildLocationTree(data);
        setLocationTree(tree);
        
        // Auto-expand nodes to show selected location
        if (selectedLocationId) {
          const newExpanded = new Set(expandedNodes);
          // Find path to selected location and expand all parent nodes
          const findAndExpandPath = (locs: Location[], targetId: string): boolean => {
            for (const loc of locs) {
              if (loc.id === targetId) {
                return true;
              }
              if (loc.children && loc.children.length > 0) {
                if (findAndExpandPath(loc.children, targetId)) {
                  newExpanded.add(loc.id);
                  return true;
                }
              }
            }
            return false;
          };
          findAndExpandPath(tree, selectedLocationId);
          setExpandedNodes(newExpanded);
        }
      } catch (error) {
        console.error('Error loading locations:', error);
      } finally {
        setLoading(false);
      }
    };

    loadLocations();
  }, [selectedLocationId]);

  const toggleExpanded = (locationId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(locationId)) {
      newExpanded.delete(locationId);
    } else {
      newExpanded.add(locationId);
    }
    setExpandedNodes(newExpanded);
  };

  const handleClearSelection = () => {
    onLocationSelect(undefined);
  };

  if (loading) {
    return (
      <FormField label={label} description={description} error={error} className={className}>
        <div className="p-4 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
          <p className="text-theme-secondary text-sm mt-2">Loading locations...</p>
        </div>
      </FormField>
    );
  }

  return (
    <FormField label={label} description={description} error={error} className={className}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {selectedLocationId && (
              <button
                type="button"
                onClick={handleClearSelection}
                className="btn btn-secondary btn-sm"
              >
                Clear Selection
              </button>
            )}
          </div>
          {showAddButton && onAddNewLocation && (
            <button
              type="button"
              onClick={onAddNewLocation}
              className="btn btn-secondary btn-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add New
            </button>
          )}
        </div>

        <div className={`border border-theme-primary rounded-md ${compact ? 'max-h-48' : 'max-h-64'} overflow-y-auto`}>
          {locationTree && locationTree.length > 0 ? (
            <div className="p-2">
              <LocationTreeNode
                locations={locationTree}
                selectedLocationId={selectedLocationId}
                expandedNodes={expandedNodes}
                toggleExpanded={toggleExpanded}
                onLocationSelect={onLocationSelect}
                compact={compact}
              />
            </div>
          ) : (
            <div className="p-4 text-center">
              <MapPin className="w-8 h-8 text-theme-muted mx-auto mb-2" />
              <p className="text-theme-secondary text-sm">No locations available</p>
              {showAddButton && onAddNewLocation && (
                <button
                  type="button"
                  onClick={onAddNewLocation}
                  className="btn btn-primary btn-sm mt-2"
                >
                  Create your first location
                </button>
              )}
            </div>
          )}
        </div>

        {selectedLocationId && (
          <div className="text-sm text-theme-secondary">
            Selected: {(() => {
              const findLocation = (locs: Location[]): string | null => {
                for (const loc of locs) {
                  if (loc.id === selectedLocationId) {
                    return loc.name;
                  }
                  if (loc.children && loc.children.length > 0) {
                    const found = findLocation(loc.children);
                    if (found) return found;
                  }
                }
                return null;
              };
              return findLocation(locationTree || []) || 'Unknown location';
            })()}
          </div>
        )}
      </div>
    </FormField>
  );
};

export default LocationTreeSelector;