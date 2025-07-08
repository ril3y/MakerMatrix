# MakerMatrix - Intelligent Parts Inventory Management System

## Overview

MakerMatrix is a comprehensive, API-first inventory management system designed specifically for makers, electronics enthusiasts, and small-scale manufacturers. Built with FastAPI and modern Python practices, it provides a robust backend for tracking, organizing, and managing electronic components, hardware parts, and materials with integrated label printing capabilities.

## Core Architecture

### Technology Stack
- **Backend Framework**: FastAPI (Python 3.10+) with async support
- **Database**: SQLite with SQLModel ORM for type-safe database operations
- **Authentication**: JWT-based OAuth2 with role-based access control
- **Validation**: Pydantic V2 for request/response validation
- **Label Printing**: Brother QL printer integration with QR code support
- **External APIs**: Integration with EasyEDA, LCSC, Mouser, and BoltDepot

### Project Structure
```
MakerMatrix/
├── api/              # External API integrations
├── database/         # Database configuration and setup
├── dependencies/     # FastAPI dependencies (auth, etc.)
├── handlers/         # Exception handlers
├── models/           # SQLModel database models
├── parsers/          # Vendor-specific part data parsers
├── printers/         # Label printer implementations
├── repositories/     # Data access layer
├── routers/          # API endpoints
├── schemas/          # Pydantic schemas
├── services/         # Business logic layer
└── tests/            # Test suite
```

## Key Features

### 1. Part Inventory Management
- **Unique Part Tracking**: Each part has a unique name, number, and identifier
- **Flexible Properties**: JSON field for custom metadata and specifications
- **Quantity Management**: Track stock levels with low-stock thresholds
- **Multi-Category Support**: Parts can belong to multiple categories
- **Location Tracking**: Hierarchical location system for physical organization
- **Advanced Search**: Filter by quantity, category, location, supplier, and custom properties

### 2. Hierarchical Location System
- **Multi-Level Organization**: Support for warehouse → shelf → bin hierarchy
- **Parent-Child Relationships**: Automatic path resolution for nested locations
- **Cascade Protection**: Prevents accidental deletion of locations with parts
- **Location Types**: Flexible classification (storage, workbench, transit, etc.)

### 3. Category Management
- **Flexible Taxonomy**: Create custom categories for your inventory
- **Many-to-Many Relationships**: Parts can belong to multiple categories
- **Bulk Operations**: Efficient category assignment and removal
- **Auto-Creation**: Categories created automatically when adding parts

### 4. Authentication & Authorization
- **JWT Tokens**: Secure, stateless authentication
- **Role-Based Access**: Multi-tier role system with granular permissions
  - **Admin**: Full system access including user management, system configuration
  - **Manager**: Inventory management, order processing, task creation
  - **User**: Standard inventory operations, parts CRUD, label printing
  - **Read-Only**: View-only access to inventory, search, and reports
- **Permission System**: Fine-grained control with hierarchical permissions
  - `parts:read`, `parts:write`, `parts:delete`
  - `categories:read`, `categories:write`, `categories:delete`
  - `locations:read`, `locations:write`, `locations:delete`
  - `orders:read`, `orders:write`, `orders:delete`
  - `tasks:read`, `tasks:write`, `tasks:admin`
  - `users:read`, `users:write`, `users:admin`
  - `system:admin`, `system:config`
- **Password Security**: Bcrypt hashing with configurable requirements

### 5. Label Printing System
- **Brother QL Support**: Network and USB printer connectivity
- **QR Code Generation**: Encode part data for quick scanning
- **Combined Labels**: QR code + human-readable text
- **Configurable Settings**: DPI, label size, margins, rotation
- **Print Queue**: Handle multiple label requests efficiently

### 6. CSV Order Import & Order Tracking
- **Multi-Vendor CSV Support**: Import order data from major suppliers
  - LCSC: Auto-detect filename patterns (LCSC_Exported__YYYYMMDD_HHMMSS.csv)
  - DigiKey: Order CSV files with comprehensive part data
  - Mouser: Standard order export format
- **Automatic Order Tracking**: Link parts to order history
- **Order Summary Statistics**: Track pricing history, order counts, supplier info
- **Modular Parser System**: Easy to add new CSV formats
- **Auto-Population**: Extract order date/number from filenames

### 7. Advanced Task-Based Enrichment System
- **Multi-Vendor Support**: Parse data from major suppliers with focused capability system
  - **LCSC**: Electronic components with specifications, datasheets, and EasyEDA integration
    - Capabilities: `get_part_details`, `fetch_datasheet`, `fetch_image`, `fetch_pricing`, `import_orders`
    - Rate limiting: Configurable (10-60 requests/minute) for responsible web scraping
    - No authentication required - uses public EasyEDA API
  - **Mouser**: Component data, images, pricing, and availability
    - Capabilities: `get_part_details`, `fetch_datasheet`, `fetch_image`, `fetch_pricing`, `fetch_stock`, `parametric_search`, `import_orders`
    - Rate limiting: 30 calls per minute, 1000 calls per day
    - API key authentication required
  - **DigiKey**: Comprehensive parametric data and high-quality images
    - Capabilities: `get_part_details`, `fetch_datasheet`, `fetch_image`, `fetch_pricing`, `fetch_stock`, `import_orders`
    - Requires client credentials (OAuth2) for API access
    - Fallback to CSV import only if API library unavailable
  - **BoltDepot**: Hardware and fastener information
    - Capabilities: `get_part_details`, `fetch_pricing`, `fetch_image`
    - Web scraping with rate limiting for hardware components
- **Simplified Capability-Based Architecture**: Streamlined supplier capability system focused on inventory enrichment
  - **Core SupplierCapability Enum**: Essential capabilities for inventory management
    - `GET_PART_DETAILS`: Get detailed part information including specifications
    - `FETCH_DATASHEET`: Download or link to part datasheets  
    - `FETCH_IMAGE`: Retrieve product images
    - `FETCH_PRICING`: Get current pricing information
    - `FETCH_STOCK`: Check inventory availability
    - `PARAMETRIC_SEARCH`: Advanced filtering by parameters
    - `IMPORT_ORDERS`: Import order files (CSV, XLS, etc.)
  - **Inventory-Focused Design**: MakerMatrix prioritizes part enrichment over discovery
    - Removed search capabilities to focus on enriching existing inventory
    - Consolidated specifications into GET_PART_DETAILS for simplified data flow
    - Users directed to supplier websites for part discovery
  - **Dynamic Capability Detection**: Suppliers declare their available capabilities based on:
    - API library availability (e.g., DigiKey requires `digikey-api` package)
    - Authentication status and credential validity
    - Configuration completeness and API endpoint accessibility
  - **Graceful Degradation**: Suppliers automatically fall back to limited capabilities when:
    - Required dependencies are missing
    - API credentials are invalid or expired
    - Network connectivity issues prevent full API access
- **EasyEDA Integration**: Direct integration with EasyEDA public API for LCSC components
  - Fetch component details, specifications, and datasheet links
  - Extract part images from LCSC product pages
  - No authentication required - uses same API as EasyEDA web interface
- **Comprehensive Background Task System**: Production-ready asynchronous processing
  - **Task Security Framework**: Role-based permissions (USER, POWER_USER, ADMIN, SYSTEM)
  - **Enhanced Parser Architecture**: Supplier capabilities system with modular design
  - **Task Queue Management**: Priority levels, retry logic, and concurrent task handling
  - **Real-time Progress Tracking**: WebSocket updates with detailed step information
  - **Individual Part Enrichment**: UI integration with "Enrich" button on part details
  - **Bulk Operations**: Process multiple parts simultaneously with batch optimization
  - **Database Safety**: Proper session management and transaction isolation
  - **API Integration**: RESTful endpoints for task creation, monitoring, and management

### 8. Modular Supplier Integration Architecture ✅
- **✅ Modernized Supplier Registry System**: Clean architecture with dynamic supplier discovery
  - **BaseSupplier Interface**: Abstract base class defining standard supplier contract
    - Capability declaration through `get_capabilities()` method
    - Dynamic configuration schema through `get_configuration_schema()`
    - Credential requirement definitions through `get_capability_requirements()`
    - Standardized authentication and connection testing
    - Rate limiting and request tracking built-in
  - **Registry Pattern**: Automatic supplier registration using `@register_supplier` decorator
    - Suppliers auto-register on import with their capability declarations
    - Dynamic supplier discovery and instantiation
    - Configuration validation and credential requirement checking
  - **Supplier Implementations**: Production-ready implementations for major suppliers
    - **LCSC**: Web scraping with EasyEDA API integration, configurable rate limiting
    - **DigiKey**: OAuth2 API with graceful degradation to CSV-only mode
    - **Mouser**: Full API support with comprehensive part data
    - **BoltDepot**: Hardware and fastener data with web scraping
- **✅ Enhanced Configuration System**: Flexible supplier configuration with validation
  - **Configuration Schema**: Dynamic field definitions with validation rules
    - Field types: TEXT, PASSWORD, URL, NUMBER, BOOLEAN, SELECT, TEXTAREA
    - Required/optional field declaration with defaults
    - Validation rules (min/max values, regex patterns, etc.)
    - Help text and user guidance for complex configurations
  - **Multiple Configuration Options**: Suppliers can offer different configuration presets
    - Standard vs. Conservative rate limiting for LCSC
    - Production vs. Sandbox modes for API-based suppliers
    - Different authentication methods per supplier capabilities
  - **Credential Management**: Secure credential storage with capability requirements
    - Field-level credential requirements per capability
    - Encrypted storage of API keys and sensitive data
    - Credential validation and expiration handling
- **✅ Capability-Based Enrichment Engine**: Intelligent capability matching and execution
  - **Capability Validation**: Pre-flight validation before task execution
    - Check supplier declares requested capabilities
    - Verify required credentials are present and valid
    - Test API connectivity and authentication status
  - **Graceful Fallback**: Automatic capability degradation for resilient operation
    - DigiKey falls back to CSV import if API library unavailable
    - LCSC adjusts rate limiting based on network conditions
    - Error-specific capability disabling with user notification
  - **Rate Limiting Integration**: Built-in rate limiting with supplier-specific rules
    - Configurable requests per minute for web scraping suppliers
    - API quota management for authenticated suppliers
    - Automatic backoff and retry logic for rate limit errors
- **✅ Frontend Integration**: Seamless UI integration with supplier capabilities
  - **Dynamic Supplier Dropdown**: Only shows suppliers with valid configurations
  - **Real-time Capability Checking**: UI updates based on current supplier status
  - **Configuration Validation**: Immediate feedback on configuration completeness
  - **Enrichment Progress**: Real-time updates during capability-based enrichment
- **✅ Enhanced Import and Export Systems**: Full integration with supplier architecture
  - **Multi-format Support**: CSV, XLS, XLSX with automatic supplier detection
  - **Order Tracking Integration**: Link imported parts to supplier order history
  - **Enrichment Queue**: Priority-based enrichment with capability-aware scheduling
  - **Error Recovery**: Intelligent retry logic with capability-specific error handling

## API Endpoints

### Parts Management
- `POST /parts/add_part` - Create new part with validation
- `GET /parts/get_part` - Retrieve by ID, name, or part number
- `PUT /parts/update_part/{id}` - Update part details
- `DELETE /parts/delete_part` - Remove part from inventory
- `GET /parts/get_all_parts` - Paginated part listing
- `POST /parts/search` - Advanced multi-criteria search

### Location Management
- `POST /locations/add_location` - Create storage location
- `GET /locations/get_location` - Retrieve location details
- `PUT /locations/update_location/{id}` - Update location info
- `DELETE /locations/delete_location/{id}` - Delete with safety checks
- `GET /locations/get_location_path` - Get full hierarchy path

### Category Operations
- `POST /categories/add_category` - Create new category
- `GET /categories/get_all_categories` - List all categories
- `PUT /categories/update_category/{id}` - Update category
- `DELETE /categories/remove_category` - Delete category

### User Management
- `POST /auth/login` - Authenticate user
- `POST /auth/logout` - Invalidate session
- `GET /users/me` - Get current user info
- `PUT /users/update_password` - Change password
- `POST /users/create` - Admin: Create new user
- `PUT /users/{id}/roles` - Admin: Assign roles

### CSV Import Operations
- `GET /api/csv/supported-types` - Get available CSV parsers
- `POST /api/csv/preview` - Preview CSV content and detect type
- `POST /api/csv/extract-filename-info` - Extract order info from filename
- `POST /api/csv/import` - Import parts with order tracking
- `POST /api/csv/parse` - Parse CSV without importing

### Printer Operations
- `POST /printer/print_label` - Print part label
- `POST /printer/print_qr` - Print QR code only
- `POST /printer/config` - Configure printer settings
- `GET /printer/current_printer` - Get active configuration

### Background Task Management
- `GET /api/tasks/` - List tasks with filtering and pagination
- `GET /api/tasks/{task_id}` - Get specific task details
- `POST /api/tasks/{task_id}/cancel` - Cancel running task
- `POST /api/tasks/{task_id}/retry` - Retry failed task
- `GET /api/tasks/stats/summary` - Get task system statistics
- `GET /api/tasks/worker/status` - Get task worker status
- `POST /api/tasks/worker/start` - Start task worker (admin)
- `POST /api/tasks/worker/stop` - Stop task worker (admin)

**Note**: Custom task creation has been removed for security reasons. Only predefined quick task creation endpoints are available.

### Quick Task Creation
- `POST /api/tasks/quick/part_enrichment` - Enrich individual part
- `POST /api/tasks/quick/datasheet_fetch` - Fetch part datasheet
- `POST /api/tasks/quick/image_fetch` - Fetch part images
- `POST /api/tasks/quick/bulk_enrichment` - Bulk enrich multiple parts
- `POST /api/tasks/quick/csv_enrichment` - Enrich CSV imported parts
- `POST /api/tasks/quick/price_update` - Update part prices
- `POST /api/tasks/quick/database_cleanup` - Database maintenance

### Task System Capabilities
- `GET /api/tasks/capabilities/suppliers` - Get all supplier capabilities
- `GET /api/tasks/capabilities/suppliers/{supplier_name}` - Get specific supplier capabilities
- `GET /api/tasks/capabilities/find/{capability_type}` - Find suppliers with capability
- `GET /api/tasks/security/permissions` - Get user task permissions
- `GET /api/tasks/security/limits` - Get user task usage limits

### Supplier Configuration Management (Planned)
- `GET /api/config/suppliers` - Get all supplier configurations
- `POST /api/config/suppliers` - Create new supplier configuration
- `GET /api/config/suppliers/{supplier_name}` - Get specific supplier config
- `PUT /api/config/suppliers/{supplier_name}` - Update supplier configuration
- `DELETE /api/config/suppliers/{supplier_name}` - Remove supplier configuration
- `POST /api/config/suppliers/{supplier_name}/test` - Test supplier API connection
- `GET /api/config/suppliers/{supplier_name}/capabilities` - Get supplier capabilities
- `POST /api/config/credentials` - Store encrypted API credentials
- `PUT /api/config/credentials/{supplier_name}` - Update supplier credentials
- `DELETE /api/config/credentials/{supplier_name}` - Remove supplier credentials
- `POST /api/config/import` - Import supplier configurations from file
- `GET /api/config/export` - Export supplier configurations

## Database Schema

### Core Tables
- **PartModel**: Main inventory items
  - Unique constraints on name and part_number
  - JSON properties field for extensibility
  - Relationships to categories and locations
  
- **LocationModel**: Storage hierarchy
  - Self-referential for parent-child relationships
  - Location types for organization
  - Cascade delete protection

- **CategoryModel**: Part categorization
  - Many-to-many with parts
  - Hierarchical support planned

- **UserModel**: System users
  - Encrypted password storage
  - Email validation
  - Active/inactive status

- **RoleModel**: Authorization roles
  - Configurable permissions with hierarchical inheritance
  - Default roles: Admin, Manager, User, Read-Only
  - Role-based endpoint protection and data filtering

### Order Tracking Tables
- **OrderModel**: Supplier order records
  - Order number, date, supplier, status
  - Financial totals (subtotal, tax, shipping)
  - Import source tracking

- **OrderItemModel**: Individual items within orders
  - Part details and quantities
  - Pricing information (unit price, extended price)
  - Links to inventory parts

- **PartOrderSummary**: Order statistics per part
  - Last order info (date, price, order number)
  - Pricing statistics (lowest, highest, average)
  - Total order count per part

### Task System Tables
- **TaskModel**: Background task management
  - Task type, status, priority, and progress tracking
  - Input/output data storage with JSON fields
  - User ownership and security context
  - Retry logic and timeout handling
  - Related entity tracking (part, order, etc.)
  - Dependency management between tasks

### Supplier Configuration Tables (Planned)
- **SupplierConfigModel**: Supplier service configuration
  - Supplier name, API type (REST/GraphQL/scraping), base URL
  - Rate limiting configuration and timeout settings
  - Custom headers and request parameters
  - Capability definitions and feature flags
  - User ownership and access control

- **SupplierCredentialsModel**: Encrypted API credentials
  - Supplier name with foreign key to SupplierConfigModel
  - Encrypted API keys, secret keys, and authentication tokens
  - Username/password for basic auth or web scraping
  - Credential rotation tracking and expiration dates
  - AES-256 encryption with user-specific salt

- **EnrichmentProfileModel**: User-defined enrichment workflows
  - Profile name and description for reusable configurations
  - Supplier priority order and fallback chains
  - Capability selection (datasheet, image, pricing, specs)
  - Custom field mappings and data transformation rules
  - Default profile designation per user/organization

## Security Features

### Authentication
- JWT tokens with configurable expiration
- Refresh token support
- Secure password hashing (bcrypt)
- Password complexity requirements

### Authorization
- Role-based access control (RBAC) with hierarchical permissions
- Granular permission system with capability-based access
- Endpoint-level security with automatic role validation
- Default deny policy with explicit permission grants

#### Role Permission Matrix

| Feature | Read-Only | User | Manager | Admin |
|---------|-----------|------|---------|-------|
| **Parts Management** |
| View parts | ✅ | ✅ | ✅ | ✅ |
| Search parts | ✅ | ✅ | ✅ | ✅ |
| Add parts | ❌ | ✅ | ✅ | ✅ |
| Edit parts | ❌ | ✅ | ✅ | ✅ |
| Delete parts | ❌ | ❌ | ✅ | ✅ |
| **Categories & Locations** |
| View categories/locations | ✅ | ✅ | ✅ | ✅ |
| Create categories/locations | ❌ | ✅ | ✅ | ✅ |
| Edit categories/locations | ❌ | ✅ | ✅ | ✅ |
| Delete categories/locations | ❌ | ❌ | ✅ | ✅ |
| **Order Management** |
| View orders | ✅ | ✅ | ✅ | ✅ |
| Import CSV orders | ❌ | ✅ | ✅ | ✅ |
| Create orders | ❌ | ❌ | ✅ | ✅ |
| Delete orders | ❌ | ❌ | ✅ | ✅ |
| **Tasks & Enrichment** |
| View task status | ✅ | ✅ | ✅ | ✅ |
| Create enrichment tasks | ❌ | ✅ | ✅ | ✅ |
| Cancel own tasks | ❌ | ✅ | ✅ | ✅ |
| Cancel any tasks | ❌ | ❌ | ✅ | ✅ |
| Task worker management | ❌ | ❌ | ❌ | ✅ |
| **User Management** |
| View own profile | ✅ | ✅ | ✅ | ✅ |
| Change own password | ✅ | ✅ | ✅ | ✅ |
| View all users | ❌ | ❌ | ❌ | ✅ |
| Create users | ❌ | ❌ | ❌ | ✅ |
| Assign roles | ❌ | ❌ | ❌ | ✅ |
| **System Administration** |
| View system logs | ❌ | ❌ | ❌ | ✅ |
| Configure suppliers | ❌ | ❌ | ❌ | ✅ |
| Database backup/restore | ❌ | ❌ | ❌ | ✅ |
| **Printing** |
| Print labels | ❌ | ✅ | ✅ | ✅ |
| Configure printers | ❌ | ❌ | ✅ | ✅ |

### Data Protection
- SQL injection prevention via ORM
- Input validation on all endpoints
- CORS configuration for API access
- Secure error handling (no sensitive data exposure)

## Use Cases

### Electronics Workshop
- Track resistors, capacitors, ICs by value and package
- Organize by project or function
- Quick lookup via QR scanning
- Low-stock alerts for common components

### Makerspace
- Shared inventory management
- User access control for different areas
- Track tool locations and availability
- Generate labels for member storage

### Small Manufacturing
- Component tracking for production
- Supplier information management
- Location tracking across warehouses
- Integration with ordering systems

### Educational Institution
- Student project component allocation
- Lab inventory management with role-based access
- Usage tracking and reporting
- Budget management integration
- Read-only access for students to view available components

### Multi-Role Scenarios

#### Corporate Environment
- **Admin**: IT administrators managing system configuration
- **Manager**: Procurement managers handling orders and suppliers  
- **User**: Engineers and technicians managing daily inventory
- **Read-Only**: Auditors, accountants, and visitors viewing inventory data

#### Shared Workshop/Makerspace
- **Admin**: Facility managers with full access
- **Manager**: Workshop coordinators managing tools and supplies
- **User**: Members with creation and modification rights
- **Read-Only**: Visitors, prospective members, or restricted access users

#### Research Institution
- **Admin**: Lab managers and system administrators
- **Manager**: Principal investigators managing project inventories
- **User**: Graduate students and researchers
- **Read-Only**: Undergraduate students, visiting researchers, safety inspectors

## Current Status

### ✅ Production Ready
- Core CRUD operations for all entities
- Authentication and authorization system
- Label printing with Brother QL printers
- Advanced search functionality
- Comprehensive error handling
- Input validation and sanitization
- CSV order import system with auto-detection
- Order tracking and pricing history
- Multi-vendor CSV parser framework
- **Task-Based Enrichment System**: Full production implementation
  - Individual part enrichment via UI
  - Background task processing with WebSocket progress
  - Role-based task security and permissions
  - API endpoints for task management and monitoring
  - Enhanced parser integration with supplier capabilities
  - Proper database session management and error handling
- **✅ Modular Supplier Integration**: Complete architecture overhaul
  - Modernized supplier registry with dependency injection
  - Enhanced parser system with separated API logic
  - Frontend supplier dropdown with configured suppliers
  - Updated import and enrichment systems
  - Removed deprecated client code and cleaned up legacy dependencies

### 🚧 In Development
- Database migration system
- Stock level notifications
- Audit trail logging
- Custom label templates
- Report generation
- Frontend order history display

### 🔮 Future Enhancements
- Multi-language support
- Mobile app API endpoints
- Barcode scanning support
- Integration with ordering systems
- Advanced analytics dashboard
- Backup and restore functionality

## Testing

The project includes a comprehensive test suite:
- **Unit Tests**: Core business logic validation
- **Integration Tests**: API endpoint testing
- **Repository Tests**: Database operation validation
- **Service Tests**: Business rule enforcement
- **Current Coverage**: ~54% with focus on critical paths

## Performance Considerations

- Async/await for non-blocking operations
- Efficient pagination for large datasets
- Indexed database fields for quick lookups
- Connection pooling for database access
- Caching strategy for frequently accessed data

## Deployment

MakerMatrix is designed for flexible deployment:
- **Development**: Built-in uvicorn server
- **Production**: Gunicorn with uvicorn workers
- **Containerization**: Docker support planned
- **Database**: SQLite for simplicity, PostgreSQL ready

## Contributing

The project follows standard Python practices:
- Type hints throughout the codebase
- Comprehensive docstrings
- Black formatting
- Pytest for testing
- Pre-commit hooks for code quality

## License

[License information to be added]

## Support

For issues, feature requests, or contributions, please refer to the project repository.