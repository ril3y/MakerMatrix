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
- **Role-Based Access**: Admin, Manager, and User roles with granular permissions
- **Permission System**: Fine-grained control (parts:create, parts:update, etc.)
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
- **Multi-Vendor Support**: Parse data from major suppliers
  - LCSC: Electronic components with specifications, datasheets, and EasyEDA integration
  - Mouser: Component data, images, pricing, and availability
  - DigiKey: Comprehensive parametric data and high-quality images
  - BoltDepot: Hardware and fastener information
- **EasyEDA Integration**: Fetch component details, footprints, and 3D models
- **Capability-Based Enrichment**: Intelligent selection of available data sources
  - Datasheet fetching from supplier APIs
  - Product image retrieval for visual identification
  - Real-time pricing and stock information
  - Detailed technical specifications
  - Component validation and verification
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
- **✅ Modernized Supplier Registry System**: Clean architecture with new supplier registry
  - Consolidated supplier system using `MakerMatrix.suppliers.registry`
  - BaseSupplier interface with standardized capabilities and methods
  - Supplier-specific implementations (LCSC, Mouser, DigiKey, BoltDepot)
  - Dependency injection pattern for enhanced parsers and services
- **✅ Updated Enhanced Parser System**: Refactored for new supplier architecture
  - Enhanced LCSC Parser V2 with dependency injection
  - Separated API communication from data parsing logic
  - Capability-based enrichment with modular design
  - Proper error handling and result transformation
- **✅ Frontend Supplier Integration**: User interface for supplier management
  - Supplier dropdown in AddPartModal using configured suppliers only
  - Dynamic supplier service for frontend API communication
  - Automatic supplier detection and configuration validation
  - Real-time supplier capability checking
- **✅ Updated Import and Enrichment Systems**: Full integration with new architecture
  - Enhanced import service with new supplier system integration
  - Updated CSV import service with proper supplier dependencies
  - Rate limiting service integration for API protection
  - Enrichment queue manager with priority-based processing

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
- `POST /api/tasks/` - Create custom background task
- `GET /api/tasks/{task_id}` - Get specific task details
- `POST /api/tasks/{task_id}/cancel` - Cancel running task
- `POST /api/tasks/{task_id}/retry` - Retry failed task
- `GET /api/tasks/stats/summary` - Get task system statistics
- `GET /api/tasks/worker/status` - Get task worker status
- `POST /api/tasks/worker/start` - Start task worker (admin)
- `POST /api/tasks/worker/stop` - Stop task worker (admin)

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
- `POST /api/tasks/security/validate` - Validate task creation

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
  - Configurable permissions
  - Default roles: Admin, Manager, User

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
- Role-based access control (RBAC)
- Granular permission system
- Endpoint-level security
- Default deny policy

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
- Lab inventory management
- Usage tracking and reporting
- Budget management integration

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