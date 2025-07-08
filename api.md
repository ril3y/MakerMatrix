# MakerMatrix API Documentation

This document provides comprehensive documentation for the MakerMatrix FastAPI application, including all data models, schemas, and API endpoints.

## Table of Contents

- [Authentication](#authentication)
- [Data Models](#data-models)
- [API Response Schema](#api-response-schema)
- [API Endpoints](#api-endpoints)
  - [Authentication Routes](#authentication-routes)
  - [Parts Management](#parts-management)
  - [Categories Management](#categories-management)
  - [Locations Management](#locations-management)
  - [User Management](#user-management)
  - [Task Management](#task-management)
  - [Order File Import](#order-file-import)
  - [AI Integration](#ai-integration)
  - [Printer Management](#printer-management)
  - [Utility Routes](#utility-routes)
  - [WebSocket Endpoints](#websocket-endpoints)

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Data Models

### Core Models

#### PartModel
Main model for electronic parts/components.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `part_number` | `str` | Supplier part number |
| `part_name` | `str` | Unique part name (required) |
| `description` | `str` | Part description |
| `quantity` | `int` | Current inventory quantity |
| `supplier` | `str` | Supplier name |
| `location_id` | `str` | Foreign key to LocationModel |
| `image_url` | `str` | URL to part image |
| `additional_properties` | `dict` | JSON field for custom properties |
| `categories` | `List[CategoryModel]` | Associated categories |
| `order_items` | `List[OrderItemModel]` | Order history |
| `order_summary` | `PartOrderSummary` | Order summary information |
| `datasheets` | `List[DatasheetModel]` | Associated datasheet files |

#### CategoryModel
Model for organizing parts into categories.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `name` | `str` | Unique category name |
| `description` | `str` | Category description |
| `part_count` | `int` | Number of parts in this category (included in API responses) |
| `parts` | `List[PartModel]` | Associated parts |

#### LocationModel
Model for tracking part storage locations.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `name` | `str` | Location name |
| `description` | `str` | Location description |
| `parent_id` | `str` | Parent location ID (for hierarchy) |
| `location_type` | `str` | Location type (default: "standard") |
| `image_url` | `str` | URL to location image (for visual identification) |
| `parent` | `LocationModel` | Parent location |
| `children` | `List[LocationModel]` | Child locations |
| `parts` | `List[PartModel]` | Parts at this location |

#### UserModel
Model for user accounts and authentication.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `username` | `str` | Unique username |
| `email` | `str` | Unique email address |
| `hashed_password` | `str` | Bcrypt hashed password |
| `is_active` | `bool` | Account active status |
| `password_change_required` | `bool` | Force password change flag |
| `created_at` | `datetime` | Account creation timestamp |
| `last_login` | `datetime` | Last login timestamp |
| `roles` | `List[RoleModel]` | User roles for permissions |

#### RoleModel
Model for role-based access control.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `name` | `str` | Unique role name |
| `description` | `str` | Role description |
| `permissions` | `List[str]` | List of permission strings |
| `users` | `List[UserModel]` | Users with this role |

### Order Management Models

#### OrderModel
Model for tracking supplier orders.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `order_number` | `str` | Supplier order number |
| `supplier` | `str` | Supplier name |
| `order_date` | `datetime` | Order placement date |
| `status` | `str` | Order status (pending, ordered, shipped, delivered, cancelled) |
| `tracking_number` | `str` | Shipping tracking number |
| `subtotal` | `float` | Order subtotal |
| `tax` | `float` | Tax amount |
| `shipping` | `float` | Shipping cost |
| `total` | `float` | Total order amount |
| `currency` | `str` | Currency code (default: USD) |
| `notes` | `str` | Order notes |
| `order_items` | `List[OrderItemModel]` | Items in the order |

#### OrderItemModel
Model for individual items within an order.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `order_id` | `str` | Foreign key to OrderModel |
| `part_id` | `str` | Foreign key to PartModel |
| `supplier_part_number` | `str` | Supplier's part number |
| `manufacturer_part_number` | `str` | Manufacturer's part number |
| `description` | `str` | Item description |
| `manufacturer` | `str` | Manufacturer name |
| `quantity_ordered` | `int` | Quantity ordered |
| `quantity_received` | `int` | Quantity received |
| `unit_price` | `float` | Price per unit |
| `extended_price` | `float` | Total price for line item |
| `status` | `str` | Item status |

### Task Management Models

#### TaskModel
Model for background task management.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID primary key |
| `task_type` | `TaskType` | Type of task (enum) |
| `name` | `str` | Task name |
| `description` | `str` | Task description |
| `status` | `TaskStatus` | Current status (enum) |
| `priority` | `TaskPriority` | Task priority (enum) |
| `progress_percentage` | `int` | Completion percentage (0-100) |
| `current_step` | `str` | Current processing step |
| `input_data` | `str` | JSON input data |
| `result_data` | `str` | JSON result data |
| `error_message` | `str` | Error message if failed |
| `max_retries` | `int` | Maximum retry attempts |
| `retry_count` | `int` | Current retry count |
| `timeout_seconds` | `int` | Task timeout |
| `created_at` | `datetime` | Creation timestamp |
| `started_at` | `datetime` | Start timestamp |
| `completed_at` | `datetime` | Completion timestamp |
| `created_by_user_id` | `str` | User who created the task |

#### Task Enums

**TaskStatus:**
- `PENDING` - Task waiting to start
- `RUNNING` - Task currently executing
- `COMPLETED` - Task finished successfully
- `FAILED` - Task encountered an error
- `CANCELLED` - Task was cancelled
- `RETRY` - Task scheduled for retry

**TaskPriority:**
- `LOW` - Low priority
- `NORMAL` - Normal priority
- `HIGH` - High priority
- `URGENT` - Urgent priority

**TaskType:**
- `CSV_ENRICHMENT` - Enrich CSV imported parts
- `PART_ENRICHMENT` - Enrich individual part
- `DATASHEET_FETCH` - Fetch part datasheet
- `IMAGE_FETCH` - Fetch part images
- `BULK_ENRICHMENT` - Bulk enrich multiple parts
- `PRICE_UPDATE` - Update part prices
- `DATABASE_CLEANUP` - Database maintenance
- `INVENTORY_AUDIT` - Audit inventory
- And more...

### Configuration Models

#### AIConfig
Configuration for AI integration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `false` | Enable AI features |
| `provider` | `str` | `"ollama"` | AI provider (ollama, openai, anthropic) |
| `api_url` | `str` | `"http://localhost:11434"` | API endpoint URL |
| `api_key` | `str` | `None` | API key for provider |
| `model_name` | `str` | `"llama3.2"` | Model name to use |
| `temperature` | `float` | `0.7` | Response temperature |
| `max_tokens` | `int` | `2000` | Maximum response tokens |
| `system_prompt` | `str` | Default prompt | System prompt for AI |

## API Response Schema

All API responses follow a consistent schema:

```json
{
  "status": "success|error|warning",
  "message": "Human readable message",
  "data": "Response data (can be any type)",
  "page": "Page number (for paginated responses)",
  "page_size": "Items per page (for paginated responses)",
  "total_parts": "Total count (for paginated responses)"
}
```

## API Endpoints

### Authentication Routes
**Base Path:** `/auth`

#### POST /auth/login
Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_string",
  "token_type": "bearer",
  "status": "success",
  "message": "Login successful"
}
```

#### POST /auth/mobile-login
JSON-only login endpoint for mobile clients.

**Request:** Same as `/auth/login`
**Response:** `ResponseSchema<Token>`

#### POST /auth/refresh
Refresh JWT token using refresh token cookie.

**Response:** New access token

#### POST /auth/logout
Logout and clear refresh token.

**Response:** Success confirmation

#### POST /users/register
Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string", 
  "password": "string",
  "roles": ["role_name"]
}
```

### Parts Management
**Base Path:** `/parts`

#### POST /parts/add_part
Add a new part to inventory.

**Request Body:**
```json
{
  "part_number": "string",
  "part_name": "string",
  "quantity": 10,
  "description": "string",
  "supplier": "string",
  "location_id": "uuid",
  "image_url": "string",
  "additional_properties": {},
  "category_names": ["category1", "category2"]
}
```

**Image Upload Workflow:**
1. First upload image using `POST /utility/upload_image`
2. Use returned image URL in `image_url` field: `/utility/get_image/{image_id}.{extension}`

**Response:** `ResponseSchema<PartResponse>`

#### GET /parts/get_all_parts
Get all parts with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10)

**Response:** `ResponseSchema<List<PartResponse>>`

#### GET /parts/get_part
Get a specific part by ID, part number, or name.

**Query Parameters:**
- `part_id`: Part UUID
- `part_number`: Supplier part number  
- `part_name`: Part name

**Response:** `ResponseSchema<PartResponse>`

#### PUT /parts/update_part/{part_id}
Update an existing part.

**Request Body:** Same as add_part (all fields optional)
**Response:** `ResponseSchema<PartResponse>`

#### DELETE /parts/delete_part
Delete a part by ID, part number, or name.

**Query Parameters:** Same as get_part
**Response:** `ResponseSchema<Dict>`

#### POST /parts/search
Advanced part search with filters.

**Request Body:**
```json
{
  "search_term": "string",
  "min_quantity": 0,
  "max_quantity": 100,
  "category_names": ["category1"],
  "location_id": "uuid",
  "supplier": "string",
  "sort_by": "part_name|part_number|quantity|location",
  "sort_order": "asc|desc",
  "page": 1,
  "page_size": 10
}
```

#### GET /parts/search_text
Simple text search across part fields.

**Query Parameters:**
- `query`: Search term (required)
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)

#### GET /parts/suggestions
Get autocomplete suggestions for part names.

**Query Parameters:**
- `query`: Search term (min 3 chars)
- `limit`: Max suggestions (default: 10)

#### DELETE /parts/clear_all
Clear all parts from database (USE WITH CAUTION).

### Categories Management
**Base Path:** `/categories`

#### GET /categories/get_all_categories
Get all categories.

**Response:** `ResponseSchema<CategoriesListResponse>`

#### POST /categories/add_category
Add a new category.

**Request Body:**
```json
{
  "name": "string",
  "description": "string"
}
```

#### PUT /categories/update_category/{category_id}
Update category information.

**Request Body:**
```json
{
  "name": "string",
  "description": "string", 
  "parent_id": "uuid"
}
```

#### GET /categories/get_category
Get category by ID or name.

**Query Parameters:**
- `category_id`: Category UUID
- `name`: Category name

#### DELETE /categories/remove_category
Remove a category.

**Query Parameters:**
- `cat_id`: Category UUID
- `name`: Category name

#### DELETE /categories/delete_all_categories
Delete all categories.

### Locations Management
**Base Path:** `/locations`

#### GET /locations/get_all_locations
Get all locations with hierarchy.

#### POST /locations/add_location
Add a new location.

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "parent_id": "uuid",
  "location_type": "standard",
  "image_url": "string"
}
```

**Image Upload Workflow:**
1. First upload image using `POST /utility/upload_image`
2. Use returned image URL in `image_url` field: `/utility/get_image/{image_id}.{extension}`

#### GET /locations/get_location
Get location by ID or name.

**Query Parameters:**
- `location_id`: Location UUID
- `name`: Location name

#### PUT /locations/update_location/{location_id}
Update location information.

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "parent_id": "uuid",
  "location_type": "standard",
  "image_url": "string"
}
```

#### GET /locations/get_location_details/{location_id}
Get detailed location information including children.

#### GET /locations/get_location_path/{location_id}
Get full path from location to root.

#### GET /locations/preview-location-delete/{location_id}
Preview what will be affected by deleting a location.

#### DELETE /locations/delete_location/{location_id}
Delete a location and handle affected parts.

#### DELETE /locations/cleanup-locations
Clean up locations with invalid parent references.

### User Management
**Base Path:** `/users`

#### POST /users/register
Register a new user. (Same as `/auth/register`)

#### GET /users/all
Get all users (admin only).

#### GET /users/{user_id}
Get user by ID.

#### GET /users/by-username/{username}
Get user by username.

#### PUT /users/{user_id}
Update user information.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "is_active": true,
  "roles": ["role_name"]
}
```

#### PUT /users/{user_id}/password
Update user password.

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

#### DELETE /users/{user_id}
Delete a user account.

### Task Management
**Base Path:** `/tasks`

#### ~~POST /tasks/~~ (REMOVED)
**SECURITY**: Custom task creation has been removed for security reasons. Use predefined quick task endpoints instead.

#### GET /tasks/
Get tasks with filtering options.

**Query Parameters:**
- `status`: Filter by status (can be multiple)
- `task_type`: Filter by task type (can be multiple)
- `priority`: Filter by priority (can be multiple)
- `created_by_user_id`: Filter by creator
- `limit`: Max results (default: 50)
- `offset`: Pagination offset (default: 0)
- `order_by`: Sort field (default: "created_at")
- `order_desc`: Sort descending (default: true)

#### GET /tasks/my
Get tasks created by current user.

#### GET /tasks/{task_id}
Get specific task by ID.

#### PUT /tasks/{task_id}
Update a task.

**Request Body:**
```json
{
  "status": "COMPLETED",
  "progress_percentage": 100,
  "current_step": "Finished",
  "result_data": {},
  "error_message": "string"
}
```

#### POST /tasks/{task_id}/cancel
Cancel a running or pending task.

#### POST /tasks/{task_id}/retry
Retry a failed task.

#### GET /tasks/types/available
Get available task types and descriptions.

#### GET /tasks/stats/summary
Get task system statistics.

#### GET /tasks/worker/status
Get task worker status.

#### POST /tasks/worker/start
Start the task worker (admin only).

#### POST /tasks/worker/stop
Stop the task worker (admin only).

### Quick Task Creation Endpoints

#### POST /tasks/quick/part_enrichment
Quick create part enrichment task.

**Request Body:**
```json
{
  "part_id": "uuid",
  "supplier": "LCSC",
  "capabilities": ["fetch_datasheet", "fetch_image"]
}
```

#### POST /tasks/quick/datasheet_fetch
Quick create datasheet fetch task.

#### POST /tasks/quick/image_fetch
Quick create image fetch task.

#### POST /tasks/quick/bulk_enrichment
Quick create bulk enrichment task.

#### POST /tasks/quick/csv_enrichment
Quick create CSV enrichment task (DEPRECATED - use file_import_enrichment).

#### POST /tasks/quick/file_import_enrichment
Quick create file import enrichment task (supports CSV, XLS, etc.).

#### POST /tasks/quick/price_update
Quick create price update task.

#### POST /tasks/quick/database_backup
Quick create database backup task (admin only).

**Request Body:**
```json
{
  "backup_name": "string (optional)",
  "include_datasheets": true,
  "include_images": true
}
```

**Parameters:**
- `backup_name`: Optional custom backup name. If not provided, will generate timestamped name like `makermatrix_backup_20240101_120000`
- `include_datasheets`: Include datasheet files in backup (default: true)
- `include_images`: Include image files in backup (default: true)

**Response:**
```json
{
  "status": "success",
  "message": "Database backup task created successfully",
  "data": {
    "id": "task_uuid",
    "task_type": "backup_creation",
    "name": "Database Backup: backup_name",
    "status": "pending",
    "priority": "high"
  }
}
```

**Note:** Requires admin permissions. Creates a comprehensive ZIP backup containing:
- SQLite database file
- All enrichment datasheet files (if included)
- All enrichment image files (if included)
- Backup metadata JSON file

Backup files are saved to `/MakerMatrix/backups/` directory.

**Alternative endpoints:**
- `POST /api/utility/backup/create` - Direct backup task creation
- `GET /api/utility/backup/download` - Legacy compatibility endpoint

### Task Capabilities

#### GET /tasks/capabilities/suppliers
Get enrichment capabilities for all suppliers.

#### GET /tasks/capabilities/suppliers/{supplier_name}
Get capabilities for specific supplier.

#### GET /tasks/capabilities/find/{capability_type}
Find suppliers with specific capability.

### Task Security

#### GET /tasks/security/permissions
Get user's task permissions and allowed task types.

#### GET /tasks/security/limits
Get user's current task usage and limits.

#### ~~POST /tasks/security/validate~~ (REMOVED)
**SECURITY**: Task validation endpoint removed along with custom task creation.

### Order File Import
**Base Path:** `/import`

#### GET /import/suppliers
Get list of suppliers that support file imports with their capabilities.

**Response:** `ResponseSchema<List<SupplierImportInfo>>`

```json
{
  "status": "success",
  "data": [
    {
      "name": "lcsc",
      "display_name": "LCSC Electronics",
      "supported_file_types": ["csv"],
      "import_available": true,
      "missing_credentials": [],
      "is_configured": true,
      "configuration_status": "configured",
      "enrichment_capabilities": ["get_part_details", "fetch_datasheet", "fetch_pricing_stock"],
      "enrichment_available": true,
      "enrichment_missing_credentials": []
    }
  ]
}
```

#### POST /import/file
Import parts from a supplier file with optional automatic enrichment.

**Request:** Form data with file upload
```http
Content-Type: multipart/form-data
supplier_name: string (required) - Supplier name (e.g., lcsc, digikey, mouser)
file: <file> (required) - Order file to import
order_number: string (optional) - Order number
order_date: string (optional) - Order date
notes: string (optional) - Order notes
enable_enrichment: boolean (optional) - Enable automatic enrichment after import (default: false)
enrichment_capabilities: string (optional) - Comma-separated list of enrichment capabilities
```

**Enrichment Capabilities:**
- `get_part_details` - Complete part info including images, specifications
- `fetch_datasheet` - Datasheet URL retrieval
- `fetch_pricing_stock` - Combined pricing and stock information

**Supported formats:** 
- CSV: LCSC, DigiKey, and other CSV formats
- XLS: Mouser Electronics order files

**Response:** `ResponseSchema<ImportResult>`

**Example Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "supplier_name=lcsc" \
  -F "file=@lcsc_order.csv" \
  -F "enable_enrichment=true" \
  -F "enrichment_capabilities=get_part_details,fetch_datasheet" \
  http://localhost:8080/api/import/file
```

### Legacy CSV Import (DEPRECATED)
**Base Path:** `/csv`

#### GET /csv/supported-types
Get list of supported order file types (CSV and XLS).

**Note:** File preview functionality has been moved to frontend-only processing for better performance and reduced server load. The frontend handles CSV parsing and supplier detection without requiring API calls.

#### POST /csv/import
Import parts from CSV text content.

**Request Body:**
```json
{
  "csv_content": "csv_string_data",
  "parser_type": "lcsc|digikey|mouser",
  "order_info": {
    "supplier": "string",
    "order_number": "string"
  }
}
```

#### POST /csv/import-file
Import uploaded CSV or XLS file.

**Request:** Form data with file upload
```http
Content-Type: multipart/form-data
file: <csv_or_xls_file>
parser_type: lcsc|digikey|mouser (optional)
order_number: string (optional)
order_date: string (optional)
notes: string (optional)
```

**Supported formats:** 
- CSV: LCSC, DigiKey, and other CSV formats
- XLS: Mouser Electronics order files

#### POST /csv/import/with-progress
Import CSV with progress tracking.

#### GET /csv/import/progress
Get current import progress.

#### POST /csv/parse
Parse CSV content without importing.

#### POST /csv/extract-filename-info
Extract order information from filename.

#### GET /csv/parsers/{parser_type}/info
Get information about specific parser.

#### GET /csv/config
Get CSV import configuration.

#### PUT /csv/config
Update CSV import configuration.

**Request Body:**
```json
{
  "download_datasheets": true,
  "download_images": true,
  "overwrite_existing_files": false,
  "download_timeout_seconds": 30,
  "show_progress": true
}
```

### AI Integration
**Base Path:** `/ai`

#### GET /ai/config
Get current AI configuration.

#### PUT /ai/config
Update AI configuration.

**Request Body:**
```json
{
  "enabled": true,
  "provider": "ollama|openai|anthropic",
  "api_url": "string",
  "api_key": "string",
  "model_name": "string",
  "temperature": 0.7,
  "max_tokens": 2000,
  "system_prompt": "string"
}
```

#### POST /ai/chat
Chat with AI assistant.

**Request Body:**
```json
{
  "message": "string",
  "conversation_history": [
    {"role": "user", "content": "string"},
    {"role": "assistant", "content": "string"}
  ]
}
```

#### POST /ai/test
Test AI connection with current configuration.

#### POST /ai/reset
Reset AI configuration to defaults.

#### GET /ai/providers
Get information about available AI providers.

#### GET /ai/models
Get available models from current AI provider.

### Printer Management
**Base Path:** `/printer`

#### POST /printer/print_label
Print a part label.

**Request Body:**
```json
{
  "part": "Part object",
  "label_size": "29x90",
  "part_name": "string"
}
```

#### POST /printer/print_qr
Print QR code for part.

#### POST /printer/config
Configure printer settings.

**Request Body:**
```json
{
  "backend": "string",
  "driver": "string", 
  "printer_identifier": "string",
  "dpi": 300,
  "model": "string",
  "scaling_factor": 1.0,
  "additional_settings": {}
}
```

#### GET /printer/load_config
Load printer configuration from file.

#### GET /printer/current_printer
Get current printer configuration.

### Utility Routes
**Base Path:** `/utility`

#### POST /utility/upload_image
Upload an image file for parts or other entities.

**Request:** Form data with file upload
```http
Content-Type: multipart/form-data
file: <image_file>
```

**Supported formats:** PNG, JPG, JPEG, GIF, WebP
**Max file size:** 5MB

**Response:**
```json
{
  "image_id": "uuid_string"
}
```

**Usage Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@part_image.png" \
  http://localhost:57891/utility/upload_image
```

#### GET /utility/get_image/{image_id}
Retrieve uploaded image by ID.

**URL Parameters:**
- `image_id`: The UUID returned from upload_image (without file extension)

**Response:** Binary image data with appropriate Content-Type header

**Usage Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:57891/utility/get_image/uuid-string.png
```

**Note:** The full image URL format is `/utility/get_image/{image_id}.{extension}`

#### GET /utility/get_counts
Get counts of parts, locations, and categories.

**Response:**
```json
{
  "status": "success",
  "message": "Counts retrieved successfully", 
  "data": {
    "parts": 150,
    "locations": 25,
    "categories": 12
  }
}
```

#### POST /utility/backup/create
Create a comprehensive database backup task (admin only).

**Response:**
```json
{
  "status": "success",
  "message": "Database backup task created successfully...",
  "data": {
    "task_id": "uuid",
    "task_type": "backup_creation",
    "backup_name": "makermatrix_backup_20240707_143000",
    "monitor_url": "/api/tasks/uuid",
    "expected_backup_location": "/MakerMatrix/backups/backup_name.zip"
  }
}
```

**Note:** Creates a background task that generates a comprehensive ZIP backup including database, datasheets, and images. Monitor progress via WebSocket or task endpoints.

#### GET /utility/backup/download
Legacy endpoint for backup creation (admin only).

**Note:** Deprecated - redirects to the new task-based backup system for backward compatibility. Use `/utility/backup/create` for new implementations.

#### GET /utility/backup/download/{backup_filename}
Download a completed backup file (admin only).

**URL Parameters:**
- `backup_filename`: Name of the backup ZIP file to download

**Response:** ZIP file download with comprehensive backup

#### GET /utility/backup/list
List all available backup files (admin only).

**Response:**
```json
{
  "status": "success", 
  "data": {
    "backups": [
      {
        "filename": "makermatrix_backup_20240707_143000.zip",
        "size_bytes": 5242880,
        "size_mb": 5.0,
        "created_at": "2024-07-07T14:30:00",
        "download_url": "/api/utility/backup/download/makermatrix_backup_20240707_143000.zip"
      }
    ]
  }
}
```

#### GET /utility/backup/export
Export all data as JSON.

**Response:** JSON file download containing all parts, locations, and categories

#### GET /utility/backup/status
Get backup status and database information.

**Response:**
```json
{
  "status": "success",
  "data": {
    "database_size": 1048576,
    "last_modified": "2024-01-01T12:00:00Z",
    "total_records": 187,
    "parts_count": 150,
    "locations_count": 25, 
    "categories_count": 12
  }
}
```

### WebSocket Endpoints

#### WS /ws/tasks
WebSocket endpoint for real-time task monitoring.

**Query Parameters:**
- `token`: JWT token for authentication

**Message Types:**
- `ping/pong`: Heartbeat
- `subscribe_task`: Subscribe to task updates
- `unsubscribe_task`: Unsubscribe from task
- `get_connection_info`: Get connection statistics

#### WS /ws/admin
WebSocket endpoint for admin monitoring (requires admin role).

**Message Types:**
- `get_system_stats`: Get system statistics
- `broadcast_notification`: Send notification to all users

## Error Handling

The API uses standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (missing or invalid token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **409**: Conflict (duplicate resource)
- **422**: Unprocessable Entity (validation errors)
- **500**: Internal Server Error

Error responses follow the standard response schema with `status: "error"` and descriptive error messages.

## Authentication & Permissions

The API uses role-based access control (RBAC) with the following key permissions:

- `parts:read` - View parts
- `parts:write` - Create/update parts
- `parts:delete` - Delete parts
- `categories:*` - Category management
- `locations:*` - Location management
- `users:*` - User management (admin)
- `tasks:*` - Task management
- `csv:import` - CSV import capabilities
- `admin` - Full administrative access

Users can have multiple roles, and roles define available permissions for API access.