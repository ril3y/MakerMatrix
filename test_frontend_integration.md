# Frontend Integration Test Plan

## What We Need to Test

Since we implemented dynamic supplier capability detection, we need to verify:

### 1. **Import Page - Supplier Selection**
- [ ] Upload a file
- [ ] Verify suppliers are loaded dynamically from `/api/import/suppliers`
- [ ] Check that supplier capabilities are displayed
- [ ] Verify configuration status is shown (configured/partial/not_configured)

### 2. **Import Page - Enrichment Options**
- [ ] Select a configured supplier (LCSC)
- [ ] Verify enrichment capabilities section appears
- [ ] Check that enrichment checkboxes are shown for available capabilities
- [ ] Verify capability icons and descriptions are displayed

### 3. **Import Process**
- [ ] Import a file without enrichment
- [ ] Import a file with enrichment capabilities selected
- [ ] Verify import progress and results
- [ ] Check that enrichment tasks are created when selected

### 4. **Error Handling**
- [ ] Try to import with unconfigured supplier
- [ ] Verify proper error messages are shown
- [ ] Check configuration warnings are displayed

## Manual Testing Steps

### Step 1: Access Frontend
1. Open browser to http://localhost:5173
2. Login with admin/Admin123!
3. Navigate to Import section

### Step 2: Test Supplier Detection
1. Upload an LCSC CSV file
2. Verify that:
   - Suppliers dropdown shows LCSC
   - LCSC shows as "configured" 
   - Other suppliers show proper status

### Step 3: Test Enrichment UI
1. Select LCSC supplier
2. Verify that enrichment options appear:
   - [ ] "Enrichment Capabilities Available" section shows
   - [ ] Checkboxes for: Part Details, Datasheets, Pricing & Stock
   - [ ] Icons are displayed correctly
   - [ ] Descriptions are clear

### Step 4: Test Import Flow
1. Select enrichment capabilities
2. Import the file
3. Verify:
   - [ ] Import succeeds
   - [ ] Enrichment task is created
   - [ ] Progress is shown

## Files to Check

The frontend changes we made:
- `ImportSelector.tsx` - Added enrichment capabilities UI
- `UnifiedFileImporter.tsx` - Added enrichment parameters to import call

## Expected Behavior

1. **Dynamic Detection**: No hard-coded suppliers
2. **Capability Display**: Only show enrichment for capable suppliers
3. **Configuration Awareness**: Show warnings for unconfigured suppliers  
4. **Seamless Integration**: Works with existing import flow