# Multi-Location Inventory Allocation System

**Date:** 2025-01-01
**Status:** Design Phase - Ready for Implementation
**Goal:** Enable parts to exist in multiple locations simultaneously with quantity tracking

---

## 🎯 Problem Statement

### Current Limitation
```python
PartModel:
  quantity: 4000           # Total across ALL locations
  location_id: "reel-1"    # Can only point to ONE location
```

**Real-World Scenario:**
```
Order: 4000 pcs of C1591 (100nF 0603 Capacitor) on reel
User cuts off 100 pcs → puts in SMD Cassette #42 for workbench use

Current system forces choice:
- Location = "Reel Storage" (loses track of cassette)
- Location = "Cassette" (loses track of main reel)
```

### The Solution: Part-Location Allocations

Track partial quantities across multiple locations:
```
Part C1591: 4000 total
  ├─ Reel Storage Shelf: 3900 pcs (primary)
  └─ SMD Cassette #42: 100 pcs (working stock)
```

---

## 🏗️ Architecture Design

### 1. New Table: PartLocationAllocation

**Purpose:** Track WHERE portions of a part exist

```python
class PartLocationAllocation(SQLModel, table=True):
    """Track partial quantities of parts across multiple locations"""
    __tablename__ = "part_location_allocations"

    # Identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_id: str = Field(foreign_key="partmodel.id", index=True)
    location_id: str = Field(foreign_key="locationmodel.id", index=True)

    # Quantity tracking
    quantity_at_location: int = Field(default=0, description="Quantity at this location")
    is_primary_storage: bool = Field(default=False, description="Main storage vs working stock")

    # Metadata
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None, description="Allocation notes")

    # Future: Smart location support (not implemented in Phase 1)
    auto_synced: bool = Field(default=False, description="Updated by smart location sensor")
    last_nfc_scan: Optional[datetime] = None

    # Relationships
    part: "PartModel" = Relationship(back_populates="allocations")
    location: "LocationModel" = Relationship()

    # Constraints
    __table_args__ = (
        UniqueConstraint('part_id', 'location_id', name='uix_part_location'),
    )
```

**Key Features:**
- One row per (part, location) pair
- `is_primary_storage` distinguishes main reel from working cassettes
- `notes` field for context ("Working stock for GC_CONTROLLER project")
- Future-proof with smart location fields (unused in Phase 1)

### 2. Update LocationModel

**Add container/cassette support:**
```python
class LocationModel(SQLModel, table=True):
    # === EXISTING FIELDS ===
    id: str
    name: str
    parent_id: Optional[str]
    location_type: str  # "bin", "shelf", "cassette", "smart_slot"
    description: Optional[str]
    image_url: Optional[str]
    emoji: Optional[str]

    # === NEW: Container Properties ===
    is_mobile: bool = Field(default=False, description="True for cassettes/containers that move")
    container_capacity: Optional[int] = Field(default=None, description="Max quantity container holds")

    # === NEW: Smart Location Support (Phase 2 - Not Implemented Yet) ===
    is_smart_location: bool = Field(default=False)
    smart_device_id: Optional[str] = Field(default=None, index=True, description="ESP32 device ID")
    smart_slot_number: Optional[int] = Field(default=None, description="Slot number in smart cabinet")
    smart_capabilities: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

    # Auto-creation (for smart locations)
    auto_created: bool = Field(default=False, description="Created by device registration")
    hidden_by_default: bool = Field(default=False, description="Don't show in main location list")

    # Connection tracking
    is_connected: bool = Field(default=False, description="Smart device connected")
    last_seen: Optional[datetime] = None
    firmware_version: Optional[str] = None
```

**Location Types:**
- **Existing:** `bin`, `shelf`, `drawer`, `cabinet`, `standard`
- **New:** `cassette`, `reel`, `tray`, `tube` (mobile containers)
- **Future:** `smart_cabinet`, `smart_slot` (IoT-enabled)

### 3. Update PartModel

**Add allocations relationship:**
```python
class PartModel(SQLModel, table=True):
    # === DEPRECATED (Keep for backward compatibility) ===
    location_id: Optional[str] = Field(...)  # Migration will convert to allocations
    quantity: Optional[int] = None           # Now computed from allocations

    # === NEW: Multiple Allocations ===
    allocations: List["PartLocationAllocation"] = Relationship(
        back_populates="part",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # === NEW: Computed Total Quantity ===
    @property
    def total_quantity(self) -> int:
        """Sum of all allocations"""
        if not hasattr(self, 'allocations') or not self.allocations:
            return self.quantity or 0  # Fallback during migration
        return sum(alloc.quantity_at_location for alloc in self.allocations)

    @property
    def primary_location(self) -> Optional["LocationModel"]:
        """Get primary storage location"""
        if not self.allocations:
            return None
        primary_alloc = next(
            (alloc for alloc in self.allocations if alloc.is_primary_storage),
            None
        )
        return primary_alloc.location if primary_alloc else None
```

---

## 📡 API Endpoints

### Part Allocation Management

**Get all allocations for a part:**
```http
GET /api/parts/{part_id}/allocations

Response:
{
  "part_id": "uuid",
  "part_name": "100nF 0603 Capacitor",
  "part_number": "C1591",
  "total_quantity": 4000,
  "allocations": [
    {
      "allocation_id": "alloc-uuid-1",
      "location_id": "reel-storage-1",
      "location_name": "Reel Storage Shelf",
      "location_path": "Office > Storage > Reel Storage Shelf",
      "location_type": "shelf",
      "quantity": 3900,
      "is_primary": true,
      "allocated_at": "2025-01-01T10:00:00Z",
      "notes": null
    },
    {
      "allocation_id": "alloc-uuid-2",
      "location_id": "cassette-42",
      "location_name": "SMD Cassette #42",
      "location_path": "Workbench > Cassette Holder > SMD Cassette #42",
      "location_type": "cassette",
      "quantity": 100,
      "is_primary": false,
      "allocated_at": "2025-01-01T12:30:00Z",
      "notes": "Working stock for GC_CONTROLLER"
    }
  ]
}
```

**Transfer quantity between locations:**
```http
POST /api/parts/{part_id}/allocations/transfer

Request:
{
  "from_location_id": "reel-storage-1",  # Required
  "to_location_id": "cassette-42",       # Required
  "quantity": 100,                        # Required
  "notes": "Working stock for assembly"  # Optional
}

Response:
{
  "status": "success",
  "message": "Transferred 100 pcs from Reel Storage Shelf to SMD Cassette #42",
  "from_allocation": {
    "location_id": "reel-storage-1",
    "new_quantity": 3800
  },
  "to_allocation": {
    "location_id": "cassette-42",
    "new_quantity": 200
  }
}
```

**Quick split to new cassette:**
```http
POST /api/parts/{part_id}/allocations/split_to_cassette

Request:
{
  "from_location_id": "reel-storage-1",
  "cassette_name": "SMD Cassette #45",
  "quantity": 100,
  "parent_location_id": "cassette-holder-1",  # Where cassette physically is
  "capacity": 200,                             # Optional: max capacity
  "notes": "Working stock"
}

Response:
{
  "status": "success",
  "message": "Created cassette and transferred 100 pcs",
  "cassette": {
    "id": "cassette-45-uuid",
    "name": "SMD Cassette #45",
    "location_type": "cassette",
    "is_mobile": true,
    "capacity": 200
  },
  "allocation": {
    "allocation_id": "alloc-uuid",
    "quantity": 100,
    "is_primary": false
  }
}
```

**Create or update allocation:**
```http
POST /api/parts/{part_id}/allocations

Request:
{
  "location_id": "cassette-42",
  "quantity": 150,
  "is_primary": false,
  "notes": "Refilled from reel"
}

# If allocation exists: updates quantity
# If allocation doesn't exist: creates new
```

**Delete allocation:**
```http
DELETE /api/parts/{part_id}/allocations/{allocation_id}

# Removes allocation record
# Does NOT delete the location itself
```

### Location Management

**Create cassette location:**
```http
POST /api/locations/create_cassette

Request:
{
  "name": "SMD Cassette #45",
  "parent_id": "cassette-holder-1",
  "container_capacity": 200,
  "emoji": "📦",
  "description": "0603 capacitors",
  "notes": "3D printed cassette"
}

Response:
{
  "id": "cassette-45-uuid",
  "name": "SMD Cassette #45",
  "location_type": "cassette",
  "is_mobile": true,
  "container_capacity": 200
}
```

---

## 🖥️ UI/UX Design

### Part Details Page - Allocations Section

**Before (Single Location):**
```
┌────────────────────────────────────┐
│ Part: C1591 100nF 0603 Capacitor   │
│ Quantity: 4000                     │
│ Location: Reel Storage Shelf       │
└────────────────────────────────────┘
```

**After (Multiple Allocations):**
```
┌─────────────────────────────────────────────────────────────┐
│ Part: C1591 - 100nF 0603 Capacitor                          │
│ Total Quantity: 4000 pcs across 2 locations                 │
│                                           [+ Split to Cassette]│
├─────────────────────────────────────────────────────────────┤
│ ALLOCATIONS                                                  │
├─────────────────────────────────────────────────────────────┤
│ Location              Path             Qty      Actions      │
├─────────────────────────────────────────────────────────────┤
│ 📦 Reel Storage      Office >          3900     [Transfer]   │
│    Shelf (Primary)   Storage                    [Update]     │
│                                                               │
│ 📍 SMD Cassette #42  Workbench >       100      [Transfer]   │
│                      Cassette Holder            [Update]     │
│                                                  [Remove]     │
│                                                               │
│ Notes: Working stock for GC_CONTROLLER                       │
└─────────────────────────────────────────────────────────────┘
```

### Split to Cassette Modal

```
┌─────────────────────────────────────────┐
│  Split to Cassette                      │
├─────────────────────────────────────────┤
│ Part: C1591 - 100nF 0603 Capacitor      │
│ Available Allocations:                   │
│                                          │
│ From Location: *                         │
│ [📦 Reel Storage Shelf (3900 pcs) ▼]    │
│                                          │
│ Quantity to Split: *                     │
│ [100] pcs                                │
│                                          │
│ To Cassette:                             │
│ ○ Existing Cassette                     │
│   [SMD Cassette #42 (100/200) ▼]       │
│                                          │
│ ● Create New Cassette                   │
│   Name: * [SMD Cassette #45]            │
│   Location: * [Cassette Holder #1 ▼]    │
│   Capacity: [200] pcs (optional)        │
│   Emoji: [📦]                            │
│                                          │
│ Notes:                                   │
│ [Working stock for next assembly]       │
│                                          │
│   [Cancel]  [Split]  [Split & Print Label]│
└─────────────────────────────────────────┘
```

### Transfer Quantity Modal

```
┌─────────────────────────────────────────┐
│  Transfer Quantity                      │
├─────────────────────────────────────────┤
│ Part: C1591 - 100nF 0603 Capacitor      │
│                                          │
│ From: *                                  │
│ [📦 Reel Storage (3900 pcs) ▼]          │
│                                          │
│ To: *                                    │
│ [📍 SMD Cassette #42 (100/200) ▼]       │
│                                          │
│ Quantity: *                              │
│ [50] pcs                                 │
│                                          │
│ Notes:                                   │
│ [Refill for assembly work]              │
│                                          │
│             [Cancel]  [Transfer]         │
└─────────────────────────────────────────┘
```

---

## 🔄 Migration Strategy

### Phase 1: Database Migration

**Goal:** Convert existing single-location parts to allocation system

**Migration Script:**
```python
# migrate_to_allocations.py

from sqlmodel import Session, select
from MakerMatrix.models.models import engine
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation

def migrate_parts_to_allocations():
    """Migrate existing parts to use allocations"""

    with Session(engine) as session:
        # Get all parts that have a location
        parts = session.exec(
            select(PartModel).where(PartModel.location_id.isnot(None))
        ).all()

        migrated_count = 0

        for part in parts:
            # Check if allocation already exists
            existing = session.exec(
                select(PartLocationAllocation).where(
                    PartLocationAllocation.part_id == part.id,
                    PartLocationAllocation.location_id == part.location_id
                )
            ).first()

            if existing:
                print(f"Allocation already exists for {part.part_name}")
                continue

            # Create allocation from existing data
            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=part.location_id,
                quantity_at_location=part.quantity or 0,
                is_primary_storage=True,  # Existing location becomes primary
                notes="Migrated from single-location system"
            )

            session.add(allocation)
            migrated_count += 1

            if migrated_count % 100 == 0:
                print(f"Migrated {migrated_count} parts...")

        session.commit()
        print(f"✅ Migration complete! Migrated {migrated_count} parts to allocations")

if __name__ == "__main__":
    migrate_parts_to_allocations()
```

**Backward Compatibility:**
- Keep `location_id` and `quantity` fields on PartModel (mark as deprecated)
- Add computed properties for smooth transition
- Frontend can check if `allocations` exists, fall back to old fields

### Phase 2: Deprecation Plan

**After allocations are stable (3-6 months):**
1. Remove `location_id` column from PartModel
2. Remove `quantity` column from PartModel
3. Update all API responses to use allocations
4. Clean up migration code

---

## 🚀 Implementation Phases

### Phase 1: Core Allocation System (Implement Now)

**Database:**
- ✅ Create `PartLocationAllocation` table
- ✅ Add `is_mobile`, `container_capacity` to LocationModel
- ✅ Add `allocations` relationship to PartModel
- ✅ Migration script for existing parts

**Backend API:**
- ✅ `GET /api/parts/{id}/allocations` - List allocations
- ✅ `POST /api/parts/{id}/allocations/transfer` - Transfer quantity
- ✅ `POST /api/parts/{id}/allocations/split_to_cassette` - Quick split
- ✅ `POST /api/parts/{id}/allocations` - Create/update allocation
- ✅ `DELETE /api/parts/{id}/allocations/{allocation_id}` - Remove allocation
- ✅ `POST /api/locations/create_cassette` - Create cassette location

**Frontend:**
- ✅ Part Details: Allocations table
- ✅ "Split to Cassette" button + modal
- ✅ Transfer quantity UI
- ✅ Create cassette integration
- ✅ Print label for cassette after creation

**Label System:**
- ✅ Cassette label template (already supported - locations work with templates)
- ✅ Template variables: `{location}`, `{part_name}`, `{part_number}`, `{quantity}`

### Phase 2: Smart Location Infrastructure (Future - Not Implemented Yet)

**WebSocket/MQTT Backend:**
- ⏳ WebSocket endpoint: `/ws/smart-locations`
- ⏳ Auto-registration API
- ⏳ Event handlers: NFC scan, quantity update, heartbeat
- ⏳ Command sender: blink LED, query slot

**Smart Location Features:**
- ⏳ Auto-create slots on device registration
- ⏳ NFC scan → part association
- ⏳ Weight sensor → quantity sync
- ⏳ LED blink commands from UI
- ⏳ Connection status monitoring

**Frontend:**
- ⏳ Smart location connection indicators
- ⏳ "Blink LED" button on smart allocations
- ⏳ Smart cabinet health dashboard
- ⏳ Hide/show auto-created slots in tree view

---

## 🎯 Use Cases

### Use Case 1: Receive Component Reel
```
1. Order arrives: 4000 pcs C1591 on reel
2. Create part (if new) or select existing
3. Create allocation:
   - Location: "Reel Storage Shelf"
   - Quantity: 4000
   - Primary: ✓
4. Print reel label
```

### Use Case 2: Split to Work Cassette
```
1. Open part C1591 details page
2. Click "Split to Cassette"
3. Select:
   - From: Reel Storage (3900 available)
   - Quantity: 100
   - Create new cassette: "SMD Cassette #45"
   - Location: Cassette Holder #1
4. Click "Split & Print Label"
5. System:
   - Reduces reel allocation: 3900 → 3800
   - Creates cassette location
   - Creates cassette allocation: 100 pcs
   - Opens print dialog for cassette label
```

### Use Case 3: Transfer Between Cassettes
```
1. Open part C1591 details
2. Click [Transfer] on Cassette #42 allocation
3. Select:
   - From: Cassette #42 (100 pcs)
   - To: Cassette #45 (50 pcs)
   - Quantity: 50
4. Click "Transfer"
5. System updates:
   - Cassette #42: 100 → 50
   - Cassette #45: 50 → 100
```

### Use Case 4: Return to Primary Storage
```
1. User finishes project, has 30 pcs left in cassette
2. Options:
   a) Transfer back to reel
   b) Delete cassette allocation (if empty)
   c) Leave in cassette for next use
```

### Use Case 5: Find Part (Future - Smart Locations)
```
1. User searches for C1591
2. System shows allocations:
   - Reel Storage: 3800 pcs
   - Smart Cabinet #1 Slot 5: 100 pcs [💡 Blink]
3. User clicks [Blink] button
4. LED blinks on smart cabinet slot 5
5. User retrieves part
6. Weight sensor detects change: 100 → 97 pcs
7. WebSocket updates backend automatically
```

---

## 🔧 Technical Notes

### Database Indexes
```sql
CREATE INDEX idx_part_location_allocation_part ON part_location_allocations(part_id);
CREATE INDEX idx_part_location_allocation_location ON part_location_allocations(location_id);
CREATE INDEX idx_location_smart_device ON locationmodel(smart_device_id);
CREATE UNIQUE INDEX uix_part_location ON part_location_allocations(part_id, location_id);
```

### Performance Considerations
- Allocations are eagerly loaded with parts (use `selectinload`)
- Total quantity is computed property (cached if needed)
- Smart location sync is async (doesn't block user operations)

### Security
- Smart devices must authenticate with JWT token
- Device registration requires admin approval (optional)
- WebSocket connections are authenticated
- Commands to devices are rate-limited

---

## 📚 Related Documentation

- **Label System:** `TEMPLATE_USER_GUIDE.md`
- **API Reference:** `api.md`
- **Database Models:** `MakerMatrix/models/`
- **Smart Location Firmware:** (Future - ESP32 project)

---

## ✅ Benefits

**Inventory Accuracy:**
- ✅ Track exact quantities at each location
- ✅ No lost/phantom inventory
- ✅ Audit trail of transfers

**Workflow Efficiency:**
- ✅ Quick split to working stock
- ✅ Easy cassette management
- ✅ Integrated label printing
- ✅ Future: Blink-to-find with smart locations

**Scalability:**
- ✅ Handle 1000+ cassettes without UI clutter
- ✅ Tree view hides auto-created smart slots
- ✅ Efficient queries with proper indexes

**Future-Proof:**
- ✅ Database schema ready for smart locations
- ✅ No breaking changes when adding IoT features
- ✅ Clean migration path
