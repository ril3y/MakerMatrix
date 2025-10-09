# Container Slot Generation Feature

**Status:** 🚧 In Progress
**Branch:** `feature/container-slot-generation`
**Started:** 2025-01-09
**Target Completion:** TBD

## Overview

Implement auto-generation of container slots to support storage containers with multiple compartments (e.g., 32-slot organizer boxes, multi-drawer toolboxes). System must be extensible to support simple, grid, and custom layouts.

## Business Problem

Currently, creating a 32-compartment storage box requires manually creating 32 individual location records. This is tedious and time-consuming. Users need:
- Quick creation of containers with many slots
- Flexible naming patterns
- Spatial organization (rows/columns)
- Support for non-uniform layouts (future)
- Multiple parts per slot (already supported via PartLocationAllocation)

## Design Principles

1. **Extensibility First** - Design for Phase 2+ from the start
2. **No Breaking Changes** - All additions, no modifications
3. **Progressive Enhancement** - Simple → Grid → Custom
4. **Data-Driven** - JSON fields for flexibility
5. **Backward Compatible** - Existing locations unaffected

## Phased Implementation

### Phase 1: Simple + Grid Layouts ✅ CURRENT PHASE

**Scope:**
- Simple linear slots (1, 2, 3, ...)
- Grid layouts (rows × columns)
- Flexible naming patterns
- Spatial metadata (row/column tracking)

**Out of Scope (Phase 2+):**
- Multi-side containers (front/back)
- Variable columns per row (2, 5, 5, 5)
- Custom layout builder UI

### Phase 2: Custom Layouts (Future)

**Scope:**
- Multiple sides (front, back, top, bottom)
- Variable columns per row
- Custom layout JSON definition
- Advanced naming patterns with {side} variable

### Phase 3: Advanced Features (Future)

**Scope:**
- Visual grid designer UI
- Container templates library
- 3D visualization
- Slot utilization analytics
- Smart container IoT integration

## Technical Architecture

### Database Schema Changes

**LocationModel additions:**
```python
# Container slot generation
slot_count: Optional[int] = None
slot_naming_pattern: Optional[str] = "Slot {n}"
slot_layout_type: Optional[str] = "simple"  # "simple" | "grid" | "custom"

# Grid layout
grid_rows: Optional[int] = None
grid_columns: Optional[int] = None

# Custom layout (Phase 2+)
slot_layout: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

# Per-slot data
is_auto_generated_slot: bool = False
slot_number: Optional[int] = None
slot_metadata: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
```

### Naming Pattern System

**Supported Variables:**
- `{n}` - Linear slot number (1, 2, 3, ...) [Phase 1]
- `{row}` - Row number (grid mode) [Phase 1]
- `{col}` - Column number (grid mode) [Phase 1]
- `{side}` - Side name (front/back/top/bottom) [Phase 2]

**Examples:**
- Simple: `"Slot {n}"` → Slot 1, Slot 2, Slot 3
- Grid: `"R{row}-C{col}"` → R1-C1, R1-C2, R2-C1
- Custom: `"{side}-R{row}-C{col}"` → front-R1-C1, back-R2-C3

### Service Layer

**New Methods:**
- `create_container_with_slots()` - Main orchestrator
- `_generate_simple_slots()` - Linear slot generation
- `_generate_grid_slots()` - Grid-based slot generation
- `_generate_custom_slots()` - Custom layout (Phase 2)
- `apply_slot_naming_pattern()` - Pattern substitution

### API Changes

**Modified Endpoints:**
- `POST /api/locations/add_location` - Accept container slot parameters

**New Query Parameters:**
- `hide_auto_slots` on `GET /api/locations/get_all_locations`

## Implementation Checklist

### Backend - Phase 1

- [x] Create feature branch `feature/container-slot-generation`
- [ ] Update LocationModel with slot fields
  - [ ] Add slot_count, slot_naming_pattern
  - [ ] Add slot_layout_type (simple/grid/custom)
  - [ ] Add grid_rows, grid_columns
  - [ ] Add slot_layout JSON field (Phase 2 ready)
  - [ ] Add is_auto_generated_slot, slot_number
  - [ ] Add slot_metadata JSON field
  - [ ] Update to_dict() method
  - [ ] Update LocationUpdate schema
- [ ] Implement LocationService methods
  - [ ] create_container_with_slots()
  - [ ] _generate_simple_slots()
  - [ ] _generate_grid_slots()
  - [ ] apply_slot_naming_pattern() helper
- [ ] Update API routes
  - [ ] Modify LocationCreateRequest schema
  - [ ] Update add_location() endpoint
  - [ ] Add hide_auto_slots to get_all_locations
  - [ ] Add validation for grid layout
- [ ] Database migration
  - [ ] Create migration script
  - [ ] Test on development DB
- [ ] Backend tests
  - [ ] Test simple slot generation
  - [ ] Test grid slot generation
  - [ ] Test naming patterns
  - [ ] Test slot metadata
  - [ ] Test cascade deletion
  - [ ] Test validation

### Frontend - Phase 1

- [ ] Update type definitions
  - [ ] Add container slot fields to Location interface
  - [ ] Add to LocationFormData type
- [ ] Update schemas
  - [ ] Add container fields to locationFormSchema
  - [ ] Add validation rules
- [ ] Update AddLocationModal
  - [ ] Add "container" to location types
  - [ ] Add layout type selector (Simple/Grid)
  - [ ] Add simple mode UI (slot count)
  - [ ] Add grid mode UI (rows/columns)
  - [ ] Add naming pattern input
  - [ ] Add live preview
  - [ ] Add validation
- [ ] Update LocationsPage
  - [ ] Add "Show auto-generated slots" toggle
  - [ ] Add filtering logic
  - [ ] Add container badge (slot count)
  - [ ] Add container icon indicator
- [ ] Update location service
  - [ ] Support new API fields
  - [ ] Add hide_auto_slots parameter
- [ ] Frontend tests
  - [ ] Test AddLocationModal container UI
  - [ ] Test layout type switching
  - [ ] Test preview generation
  - [ ] Test slot filtering
  - [ ] Test form validation

### Documentation

- [ ] Update api.md
  - [ ] Document new location fields
  - [ ] Document container creation workflow
  - [ ] Add API examples
- [ ] Update CLAUDE.md (if needed)
  - [ ] Document container feature
  - [ ] Add development notes
- [ ] Create user documentation
  - [ ] How to create containers
  - [ ] Naming pattern guide
  - [ ] Examples and screenshots

### Testing & QA

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing
  - [ ] Create 32-slot simple container
  - [ ] Create 4×8 grid container
  - [ ] Test various naming patterns
  - [ ] Assign multiple parts to one slot
  - [ ] Delete container (verify cascade)
  - [ ] Filter auto-generated slots
  - [ ] Test with existing locations (backward compat)
- [ ] Performance testing
  - [ ] Test with 100+ slots
  - [ ] Test location tree rendering

### Deployment

- [ ] Code review
- [ ] Merge to main
- [ ] Push to remote
- [ ] Database migration in production
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Smoke tests in production

## Progress Log

### 2025-01-09
- Created feature branch `feature/container-slot-generation`
- Started LocationModel updates
- Created this tracking document

## Example Usage

### Create Simple Container
```json
POST /api/locations/add_location
{
  "name": "Yellow Storage Box #1",
  "location_type": "container",
  "slot_layout_type": "simple",
  "slot_count": 32,
  "slot_naming_pattern": "Compartment {n}"
}
```

**Result:** Creates 33 locations:
- 1 container: "Yellow Storage Box #1"
- 32 slots: "Compartment 1" through "Compartment 32"

### Create Grid Container
```json
POST /api/locations/add_location
{
  "name": "Husky Toolbox",
  "location_type": "container",
  "slot_layout_type": "grid",
  "grid_rows": 4,
  "grid_columns": 8,
  "slot_naming_pattern": "R{row}-C{col}"
}
```

**Result:** Creates 33 locations:
- 1 container: "Husky Toolbox"
- 32 slots: "R1-C1", "R1-C2", ..., "R4-C8"

### Assign Multiple Parts to One Slot
```json
// Already works via existing PartLocationAllocation!
POST /api/parts/{resistor-id}/allocations
{
  "location_id": "compartment-5-uuid",
  "quantity": 100
}

POST /api/parts/{capacitor-id}/allocations
{
  "location_id": "compartment-5-uuid",
  "quantity": 50
}
```

## Future Phase 2 Example (Reference)

### Create Multi-Side Container with Variable Rows
```json
POST /api/locations/add_location
{
  "name": "Yellow Storage Box #1",
  "location_type": "container",
  "slot_layout_type": "custom",
  "slot_naming_pattern": "{side}-R{row}-C{col}",
  "slot_layout": {
    "sides": [
      {
        "name": "front",
        "rows": [
          {"row": 1, "slots": 2},
          {"row": 2, "slots": 5},
          {"row": 3, "slots": 5},
          {"row": 4, "slots": 5}
        ]
      },
      {
        "name": "back",
        "rows": [
          {"row": 1, "slots": 2},
          {"row": 2, "slots": 5},
          {"row": 3, "slots": 5},
          {"row": 4, "slots": 5}
        ]
      }
    ]
  }
}
```

**Result:** Creates 35 locations:
- 1 container: "Yellow Storage Box #1"
- 34 slots: "front-R1-C1", "front-R1-C2", "front-R2-C1", ..., "back-R4-C5"

## Extension Points

### Adding New Layout Types (Phase 2+)

**Steps:**
1. Add new value to `slot_layout_type` enum
2. Create new `_generate_X_slots()` method in LocationService
3. Add elif branch in `create_container_with_slots()`
4. Update UI with new radio option
5. No changes needed to existing code!

**Extensibility Features:**
- ✅ JSON fields (`slot_layout`, `slot_metadata`) - open-ended
- ✅ Enum pattern - easy to add values
- ✅ Generator pattern - isolated slot creation logic
- ✅ Metadata-driven naming - supports any variable
- ✅ No hard-coding - all layout logic data-driven

## Known Limitations

### Phase 1
- Cannot handle variable columns per row (need Phase 2)
- Single-side containers only (need Phase 2)
- No visual grid designer (need Phase 3)

### All Phases
- Maximum 200 slots per container (configurable)
- Naming pattern limited to 100 characters

## Questions & Decisions

### Resolved
- **Q:** Should slots be separate table or child locations?
  **A:** Child locations - leverages existing infrastructure, enables full location features

- **Q:** How to handle multiple parts per slot?
  **A:** Already works via PartLocationAllocation - no changes needed!

- **Q:** Start with full custom or MVP?
  **A:** MVP (simple + grid), then Phase 2 for custom

### Open
- None currently

## References

- **Related Models:** `LocationModel`, `PartLocationAllocation`
- **Related Services:** `LocationService`, `PartAllocationService`
- **Related Routes:** `/api/locations/*`
- **Related UI:** `AddLocationModal`, `LocationsPage`

## Team Notes

- Branch protection: Ensure all tests pass before merge
- Code review required before merge to main
- Database migration must be tested on staging first
- Document any deviations from this plan in Progress Log

---

**Last Updated:** 2025-01-09
**Document Owner:** Development Team
**Status:** Living document - update as work progresses
