# API Reference

MakerMatrix exposes a REST API built with FastAPI. All endpoints (except auth) require a valid JWT token or API key.

**Base URL**: `http://localhost:8000/api` (development) or `http://localhost:8080/api` (Docker)

## Authentication

### Login

```
POST /auth/login
Content-Type: application/json

{"username": "admin", "password": "Admin123!"}
```

Response includes an access token. Include it in subsequent requests:

```
Authorization: Bearer <access_token>
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Login (form or JSON body) |
| POST | `/auth/mobile-login` | Mobile login with refresh token |
| POST | `/auth/mobile-refresh` | Refresh mobile access token |
| POST | `/auth/refresh` | Cookie-based token refresh |
| POST | `/auth/logout` | Clear session |
| POST | `/auth/guest-login` | 24-hour guest session |

## Parts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/parts/add_part` | Create a part (with optional auto-enrichment) |
| GET | `/api/parts/get_all_parts` | List all parts (paginated) |
| GET | `/api/parts/get_part` | Get by ID, part_number, or part_name |
| GET | `/api/parts/get_part_counts` | Total part count |
| PUT | `/api/parts/update_part/{part_id}` | Update part fields |
| DELETE | `/api/parts/delete_part` | Delete by identifier |
| POST | `/api/parts/search` | Advanced search with filters |
| GET | `/api/parts/search_text` | Quick text search |
| GET | `/api/parts/suggestions` | Autocomplete suggestions |
| POST | `/api/parts/parts/{part_id}/transfer` | Transfer between locations |
| POST | `/api/parts/enrich-from-supplier` | Enrich part from supplier |
| POST | `/api/parts/bulk_update` | Bulk update multiple parts |
| POST | `/api/parts/bulk_delete` | Bulk delete multiple parts |
| DELETE | `/api/parts/clear_all` | Clear all parts (admin) |

## Locations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/locations/get_all_locations` | All locations |
| GET | `/api/locations/get_location` | Get by ID or name |
| GET | `/api/locations/get_location_details/{id}` | Location with children |
| GET | `/api/locations/get_location_path/{id}` | Full path to root |
| POST | `/api/locations/add_location` | Create (with optional slot generation) |
| PUT | `/api/locations/update_location/{id}` | Update location |
| DELETE | `/api/locations/delete_location/{id}` | Delete (with cascade options) |
| GET | `/api/locations/get_container_slots/{id}` | Container slots with occupancy |
| GET | `/api/locations/preview-location-delete/{id}` | Deletion impact preview |

## Categories

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/categories/get_all_categories` | All categories |
| GET | `/api/categories/get_category` | Get by ID or name |
| POST | `/api/categories/add_category` | Create category |
| PUT | `/api/categories/update_category/{id}` | Update category |
| DELETE | `/api/categories/remove_category` | Delete category |

## Tools

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/tools/` | Create tool |
| GET | `/api/tools/` | List all tools |
| GET | `/api/tools/{tool_id}` | Get tool by ID |
| PUT | `/api/tools/{tool_id}` | Update tool |
| DELETE | `/api/tools/{tool_id}` | Delete tool |
| POST | `/api/tools/{tool_id}/checkout` | Check out tool |
| POST | `/api/tools/{tool_id}/return` | Return tool |
| POST | `/api/tools/{tool_id}/maintenance` | Log maintenance |
| GET | `/api/tools/statistics` | Tool statistics |

## Projects

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/projects/` | All projects |
| POST | `/api/projects/` | Create project |
| GET | `/api/projects/{project_id}` | Get project |
| PUT | `/api/projects/{project_id}` | Update project |
| DELETE | `/api/projects/{project_id}` | Delete project |

## Tags

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/tags` | Create tag |
| GET | `/api/tags/` | All tags |
| GET | `/api/tags/{tag_id}` | Get tag by ID |
| PUT | `/api/tags/{tag_id}` | Update tag |
| DELETE | `/api/tags/{tag_id}` | Delete tag |
| POST | `/api/tags/{tag_id}/merge` | Merge tags |
| GET | `/api/tags/statistics` | Tag statistics |

## API Keys

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/api-keys/` | Create API key |
| GET | `/api/api-keys/` | List your keys |
| GET | `/api/api-keys/{key_id}` | Get specific key |
| PUT | `/api/api-keys/{key_id}` | Update key |
| DELETE | `/api/api-keys/{key_id}` | Delete key |
| POST | `/api/api-keys/{key_id}/revoke` | Revoke key |
| GET | `/api/api-keys/permissions/available` | Available permissions |
| GET | `/api/api-keys/admin/all` | All keys (admin) |

## Suppliers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/suppliers/` | Available suppliers |
| GET | `/api/suppliers/dropdown` | Configured suppliers for UI |
| GET | `/api/suppliers/{supplier}/info` | Supplier details |
| POST | `/api/suppliers/{supplier}/configure` | Set credentials |
| POST | `/api/suppliers/{supplier}/search` | Search parts |
| POST | `/api/suppliers/{supplier}/enrich` | Enrich part data |

## Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tasks/` | List tasks (filterable) |
| GET | `/api/tasks/my` | Current user's tasks |
| GET | `/api/tasks/types/available` | Available task types |
| GET | `/api/tasks/{task_id}` | Get task details |
| PUT | `/api/tasks/{task_id}` | Update task |
| DELETE | `/api/tasks/{task_id}` | Cancel task |

## Backup

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/backup/create` | Create encrypted backup |
| GET | `/api/backup/list` | List backups |
| POST | `/api/backup/restore` | Restore from backup |
| DELETE | `/api/backup/{backup_id}` | Delete backup |
| GET | `/api/backup/config` | Backup configuration |
| POST | `/api/backup/config` | Update backup config |

## Printer

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/printer/drivers` | Supported printer drivers |
| POST | `/api/printer/register` | Register a printer |
| GET | `/api/printer/list` | List registered printers |
| POST | `/api/printer/print-qr` | Print QR code label |
| POST | `/api/printer/print-text` | Print text label |
| POST | `/api/printer/print/template` | Print using template |
| POST | `/api/printer/preview/template` | Preview template label |

## Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/templates/` | List templates (filterable) |
| GET | `/api/templates/{id}` | Get template |
| POST | `/api/templates/` | Create template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |
| POST | `/api/templates/{id}/duplicate` | Duplicate template |
| GET | `/api/templates/categories` | Template categories |
| POST | `/api/templates/search/` | Search templates |

## Users

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/users/register` | Register user (admin) |
| GET | `/api/users/me` | Current user info |
| GET | `/api/users/` | List all users (admin) |
| PUT | `/api/users/{user_id}` | Update user |
| DELETE | `/api/users/{user_id}` | Delete user |
| POST | `/api/users/{user_id}/change-password` | Change password |

## Utility

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/utility/get_counts` | Inventory counts (also health check) |
| POST | `/api/utility/upload_image` | Upload image |
| GET | `/api/utility/image/{image_id}` | Retrieve image |
| POST | `/api/utility/import-csv` | Import CSV data |
| POST | `/api/utility/export` | Export data |

## WebSocket

Connect to `/ws/` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/')
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // data.type: 'part_created', 'part_updated', 'task_progress', etc.
}
```

## Interactive Docs

FastAPI auto-generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
