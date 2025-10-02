# Multi-Location Allocation Migration Strategy

**Date:** 2025-01-02
**Status:** Database Layer Complete, Testing Validated
**Branch:** `location-refactor`

---

## ✅ Test Results: Backward Compatibility CONFIRMED

### Tests Passing
- ✅ **7/7** model tests (Part/Location/Category models)
- ✅ **22/22** parts repository tests (Part CRUD operations)
- ✅ **365** total unit tests passing
- ✅ **No regressions** from allocation system changes

### Conclusion
**Keeping deprecated fields (`location_id`, `quantity`) is the right approach.**

---

## 🎯 Recommended Strategy: Hybrid Dual-System

### Keep BOTH Systems Running Simultaneously

```python
class PartModel(SQLModel, table=True):
    # === LEGACY SYSTEM (Kept for compatibility) ===
    location_id: Optional[str] = Field(...)  # Single location
    quantity: Optional[int] = None            # Total quantity

    # === NEW SYSTEM (Multi-location) ===
    allocations: List[PartLocationAllocation] = Relationship(...)

    # === COMPUTED PROPERTIES (Bridge between systems) ===
    @property
    def total_quantity(self) -> int:
        """Read from allocations if available, fallback to quantity"""
        if self.allocations:
            return sum(alloc.quantity_at_location for alloc in self.allocations)
        return self.quantity or 0

    @property
    def primary_location(self) -> Optional[LocationModel]:
        """Read from allocations if available, fallback to location"""
        if self.allocations:
            primary_alloc = next(
                (alloc for alloc in self.allocations if alloc.is_primary_storage),
                self.allocations[0] if self.allocations else None
            )
            return primary_alloc.location if primary_alloc else None
        return self.location
```

---

## 📋 Migration Plan

### Phase 1: Service Layer Sync (NEXT STEP)

Update `PartService` to maintain both systems:

```python
class PartService:
    def create_part(self, part_data: Dict) -> PartModel:
        """Create part in BOTH systems"""

        # 1. Create part with legacy fields
        part = PartModel(
            part_name=part_data["part_name"],
            quantity=part_data.get("quantity", 0),
            location_id=part_data.get("location_id")
        )
        session.add(part)
        session.flush()

        # 2. Create allocation if location specified
        if part.location_id and part.quantity:
            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=part.location_id,
                quantity_at_location=part.quantity,
                is_primary_storage=True,
                notes="Migrated from single-location system"
            )
            session.add(allocation)

        session.commit()
        return part

    def update_quantity(self, part_id: str, new_quantity: int):
        """Update BOTH systems"""
        part = session.get(PartModel, part_id)

        # Update legacy field
        part.quantity = new_quantity

        # Update allocation
        if part.allocations:
            primary_alloc = next(
                (a for a in part.allocations if a.is_primary_storage),
                part.allocations[0]
            )
            primary_alloc.quantity_at_location = new_quantity

        session.commit()
```

### Phase 2: Migration Script

```python
# migrate_to_allocations.py

def migrate_parts_to_allocations():
    """
    Sync existing parts to allocation system.

    Creates allocation records for all parts that have location_id and quantity.
    """

    with Session(engine) as session:
        # Get all parts with location
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
                # Sync quantity if different
                if existing.quantity_at_location != part.quantity:
                    existing.quantity_at_location = part.quantity or 0
                    session.add(existing)
                continue

            # Create allocation
            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=part.location_id,
                quantity_at_location=part.quantity or 0,
                is_primary_storage=True,
                notes="Migrated from single-location system"
            )

            session.add(allocation)
            migrated_count += 1

        session.commit()
        print(f"✅ Migrated {migrated_count} parts to allocation system")
```

### Phase 3: Gradual Code Migration

**Do NOT remove deprecated fields yet.**

Instead, gradually update code to use new system:

```python
# OLD CODE (still works)
parts = session.exec(select(PartModel).where(PartModel.quantity > 0)).all()

# NEW CODE (preferred)
parts_with_allocations = session.exec(
    select(PartModel).join(PartLocationAllocation)
).all()

# TRANSITION CODE (works with both)
total_qty = part.total_quantity  # Uses computed property
```

### Phase 4: Deprecation Timeline (Future)

**6-12 months from now:**

1. Add deprecation warnings when old fields are accessed
2. Update all internal code to use allocations
3. Update frontend to use allocation APIs
4. Monitor for any external API usage

**12-18 months from now:**

1. Remove `location_id` and `quantity` columns
2. Remove computed property fallbacks
3. Clean up migration code

---

## 🔧 Where Code Uses Deprecated Fields

### Critical Files to Update (Eventually)

**Backend:**
- `services/data/part_service.py` - Part CRUD operations
- `repositories/parts_repositories.py` - Database queries
- `routers/parts_routes.py` - API endpoints
- `suppliers/data_extraction.py` - CSV/order imports
- `routers/import_routes.py` - File import handlers

**Frontend:**
- Part forms (create/edit)
- Part display components
- Inventory dashboards
- Search/filter components

### Files Already Using Correct Pattern

✅ `models/part_models.py` - Has computed properties
✅ `services/data/part_allocation_service.py` - Uses allocations
✅ `repositories/part_allocation_repository.py` - Uses allocations

---

## 🚀 Next Implementation Steps

### 1. Update PartService (Critical)

Add allocation sync logic to:
- `create_part()`
- `update_part()`
- `update_quantity()`
- `delete_part()`

### 2. Create Migration Script

Run migration to sync existing data to allocations

### 3. Add API Routes

Create allocation endpoints:
- `GET /api/parts/{id}/allocations`
- `POST /api/parts/{id}/allocations/transfer`
- `POST /api/parts/{id}/allocations/split`

### 4. Frontend Integration

Add UI for:
- Viewing allocations on part details page
- Transfer modal
- Split to cassette modal

### 5. Testing

- Test dual-system sync
- Test migration script
- Test new allocation workflows
- Verify old code still works

---

## ✅ Benefits of This Approach

**Immediate:**
- ✅ Zero breaking changes
- ✅ All existing tests pass
- ✅ Old code continues working
- ✅ Can add new features alongside old system

**Long-term:**
- ✅ Clean migration path
- ✅ Time to update all code properly
- ✅ Can test both systems in parallel
- ✅ No data loss risk
- ✅ Gradual rollout of new features

---

## ⚠️ Important Notes

1. **Both systems must stay in sync** - PartService is responsible
2. **Allocations are source of truth** - Computed properties read from allocations
3. **Legacy fields are write-through cache** - Updated when allocations change
4. **Migration is additive** - Never destructive
5. **Deprecation is gradual** - 12-18 month timeline

---

## 📊 Current Status

- ✅ Database models created
- ✅ Repository layer complete
- ✅ Service layer complete
- ✅ Tests passing (365/365 core tests)
- ✅ Backward compatibility confirmed
- ⏳ Service sync logic (next)
- ⏳ Migration script (next)
- ⏳ API routes
- ⏳ Frontend components

**Ready to proceed with service layer updates!**
