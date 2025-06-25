# Supplier Architecture and Price Update Support

## Overview

MakerMatrix uses a modular supplier system where each supplier implements the `BaseSupplier` interface. The price update task has been fixed to use this system directly instead of the older enhanced parser system.

## Supplier Architecture

### Base Components

1. **BaseSupplier** (`/suppliers/base.py`)
   - Abstract base class defining the supplier interface
   - Provides automatic API tracking and rate limiting
   - Defines capabilities using the `SupplierCapability` enum
   - Key methods:
     - `fetch_pricing()` - Fetch current pricing for a part
     - `fetch_stock()` - Fetch current stock level
     - `fetch_datasheet()` - Fetch datasheet URL
     - `fetch_image()` - Fetch image URL
     - `fetch_specifications()` - Fetch technical specifications

2. **SupplierRegistry** (`/suppliers/registry.py`)
   - Central registry for discovering and instantiating suppliers
   - Provides factory pattern for getting supplier instances
   - Automatically discovers suppliers when imported

### Pricing Support by Supplier

| Supplier | Class | Pricing Support | Implementation Details |
|----------|-------|-----------------|------------------------|
| **DigiKey** | `DigiKeySupplier` | ✅ Yes | - Implements `fetch_pricing()` method<br>- Returns list of price breaks with quantity/price/currency<br>- Uses official DigiKey API library<br>- Supports both sandbox and production modes |
| **Mouser** | `MouserSupplier` | ✅ Yes | - Implements `fetch_pricing()` method<br>- Parses price breaks from API response<br>- Returns structured pricing data<br>- API key authentication |
| **LCSC** | `LCSCSupplier` | ❌ No | - Does NOT implement `fetch_pricing()`<br>- Uses EasyEDA API which doesn't provide pricing<br>- Would need to scrape LCSC website for prices |
| **McMaster-Carr** | `McMasterCarrSupplier` | ❌ No | - Does NOT list `FETCH_PRICING` capability<br>- Official API implementation (requires approval)<br>- Could be added with API support |
| **Bolt Depot** | `BoltDepotSupplier` | ✅ Yes* | - Lists `FETCH_PRICING` capability<br>- Uses web scraping to extract pricing tables<br>- No authentication required<br>- *Fixed to return correct format |

## Price Update Task Implementation

The price update task (`/tasks/price_update_task.py`) has been updated to:

1. Use `SupplierRegistry` to get supplier instances
2. Check if supplier supports `SupplierCapability.FETCH_PRICING`
3. Configure supplier with credentials from `SupplierConfigService`
4. Call `supplier.fetch_pricing()` directly
5. Parse pricing data (list of price breaks) to extract unit price
6. Respect supplier-specific rate limits using `supplier.get_rate_limit_delay()`

### Key Changes from Old Implementation

**Old (Enhanced Parser):**
```python
parser = get_enhanced_parser(supplier)
pricing_result = await parser.fetch_pricing(part)
```

**New (Supplier System):**
```python
supplier = SupplierRegistry.get_supplier(supplier_name)
supplier.configure(config.credentials, config.config)
pricing_data = await supplier.fetch_pricing(part.part_number)
```

## Adding Pricing Support to a Supplier

To add pricing support to a supplier that doesn't have it:

1. Add `SupplierCapability.FETCH_PRICING` to the capabilities list in `get_capabilities()`
2. Implement the `fetch_pricing()` method:

```python
async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch current pricing for a part"""
    async def _impl():
        # Your implementation here
        # Should return a list of price breaks:
        # [
        #     {"quantity": 1, "price": 1.23, "currency": "USD"},
        #     {"quantity": 10, "price": 1.10, "currency": "USD"},
        #     {"quantity": 100, "price": 0.95, "currency": "USD"}
        # ]
        pass
    
    return await self._tracked_api_call("fetch_pricing", _impl)
```

## Rate Limiting

Each supplier defines its own rate limit delay:

- **DigiKey**: 4.0 seconds (conservative for 1000/hour limit)
- **Mouser**: 2.0 seconds (for 30/minute limit)
- **LCSC**: 1.0 second (for 60/minute limit)

The price update task automatically respects these limits.

## Configuration Requirements

For price updates to work:

1. Supplier must be registered in the system
2. Supplier must be configured with valid credentials
3. Supplier must support the `FETCH_PRICING` capability
4. Part must have a valid `part_number` that the supplier recognizes

## Error Handling

The task handles various failure scenarios:

- Supplier not in registry
- Supplier not configured
- Supplier doesn't support pricing
- API errors during price fetch
- Invalid pricing data format

Failed updates are tracked and reported in the task result.