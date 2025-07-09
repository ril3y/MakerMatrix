# API Route Analysis for Comprehensive Testing

## Total Routes: 183 API endpoints

### 1. Authentication Routes (5 routes)
- POST /auth/login
- POST /auth/logout  
- POST /auth/mobile-login
- POST /auth/mobile-refresh
- POST /auth/refresh

### 2. User Management Routes (10 routes)
- GET /api/users/all
- GET /api/users/by-username/{username}
- POST /api/users/register
- GET /api/users/{user_id}
- PUT /api/users/{user_id}
- DELETE /api/users/{user_id}
- PUT /api/users/{user_id}/password
- POST /api/users/roles/add_role
- GET /api/users/roles/by-name/{name}
- GET /api/users/roles/{role_id}
- PUT /api/users/roles/{role_id}
- DELETE /api/users/roles/{role_id}

### 3. Parts Management Routes (11 routes)
- POST /api/parts/add_part
- GET /api/parts/get_all_parts
- GET /api/parts/get_part
- PUT /api/parts/update_part/{part_id}
- DELETE /api/parts/delete_part
- DELETE /api/parts/clear_all
- GET /api/parts/get_part_counts
- POST /api/parts/search
- GET /api/parts/search_text
- GET /api/parts/suggestions

### 4. Categories Management Routes (6 routes)
- POST /api/categories/add_category
- GET /api/categories/get_all_categories
- GET /api/categories/get_category
- PUT /api/categories/update_category/{category_id}
- DELETE /api/categories/remove_category
- DELETE /api/categories/delete_all_categories

### 5. Locations Management Routes (9 routes)
- POST /api/locations/add_location
- GET /api/locations/get_all_locations
- GET /api/locations/get_location
- PUT /api/locations/update_location/{location_id}
- DELETE /api/locations/delete_location/{location_id}
- GET /api/locations/get_location_details/{location_id}
- GET /api/locations/get_location_path/{location_id}
- GET /api/locations/preview-location-delete/{location_id}
- DELETE /api/locations/cleanup-locations

### 6. Task Management Routes (22 routes)
- GET /api/tasks/
- GET /api/tasks/my
- GET /api/tasks/{task_id}
- PUT /api/tasks/{task_id}
- DELETE /api/tasks/{task_id}
- POST /api/tasks/{task_id}/cancel
- POST /api/tasks/{task_id}/retry
- GET /api/tasks/types/available
- GET /api/tasks/stats/summary
- GET /api/tasks/worker/status
- POST /api/tasks/worker/start
- POST /api/tasks/worker/stop
- GET /api/tasks/security/permissions
- GET /api/tasks/security/limits
- GET /api/tasks/capabilities/suppliers
- GET /api/tasks/capabilities/suppliers/{supplier_name}
- GET /api/tasks/capabilities/find/{capability_type}
- POST /api/tasks/quick/part_enrichment
- POST /api/tasks/quick/datasheet_fetch
- POST /api/tasks/quick/image_fetch
- POST /api/tasks/quick/bulk_enrichment
- POST /api/tasks/quick/price_update
- POST /api/tasks/quick/database_backup

### 7. Import Routes (2 routes)
- POST /api/import/file
- GET /api/import/suppliers

### 8. Supplier Management Routes (32 routes)
- GET /api/suppliers/
- GET /api/suppliers/configured
- GET /api/suppliers/dropdown
- GET /api/suppliers/info
- GET /api/suppliers/{supplier_name}/info
- GET /api/suppliers/{supplier_name}/capabilities
- GET /api/suppliers/{supplier_name}/config-schema
- POST /api/suppliers/{supplier_name}/config-schema-with-config
- GET /api/suppliers/{supplier_name}/credentials-schema
- POST /api/suppliers/{supplier_name}/credentials-schema-with-config
- GET /api/suppliers/{supplier_name}/env-defaults
- POST /api/suppliers/{supplier_name}/test
- POST /api/suppliers/{supplier_name}/credentials
- GET /api/suppliers/{supplier_name}/credentials
- DELETE /api/suppliers/{supplier_name}/credentials
- GET /api/suppliers/{supplier_name}/credentials/status
- POST /api/suppliers/{supplier_name}/credentials/test
- GET /api/suppliers/{supplier_name}/credentials/test-existing
- POST /api/suppliers/{supplier_name}/oauth/authorization-url
- GET /api/suppliers/{supplier_name}/oauth/callback
- POST /api/suppliers/{supplier_name}/oauth/exchange
- POST /api/suppliers/{supplier_name}/part/{part_number}
- POST /api/suppliers/{supplier_name}/part/{part_number}/datasheet
- POST /api/suppliers/{supplier_name}/part/{part_number}/pricing
- POST /api/suppliers/{supplier_name}/part/{part_number}/stock
- GET /api/suppliers/config/suppliers
- POST /api/suppliers/config/suppliers
- GET /api/suppliers/config/suppliers/{supplier_name}
- PUT /api/suppliers/config/suppliers/{supplier_name}
- DELETE /api/suppliers/config/suppliers/{supplier_name}
- GET /api/suppliers/config/suppliers/{supplier_name}/config-fields
- GET /api/suppliers/config/suppliers/{supplier_name}/config-options
- GET /api/suppliers/config/suppliers/{supplier_name}/credential-fields
- POST /api/suppliers/config/credentials
- PUT /api/suppliers/config/credentials/{supplier_name}
- DELETE /api/suppliers/config/credentials/{supplier_name}
- GET /api/suppliers/config/export
- POST /api/suppliers/config/import
- POST /api/suppliers/config/initialize-defaults

### 9. Printer Management Routes (14 routes)
- GET /api/printer/drivers
- GET /api/printer/drivers/{driver_type}
- GET /api/printer/printers
- POST /api/printer/register
- GET /api/printer/printers/{printer_id}
- PUT /api/printer/printers/{printer_id}
- DELETE /api/printer/printers/{printer_id}
- GET /api/printer/printers/{printer_id}/status
- POST /api/printer/printers/{printer_id}/test
- POST /api/printer/test-setup
- POST /api/printer/print/text
- POST /api/printer/print/qr
- POST /api/printer/print/image
- POST /api/printer/print/advanced

### 10. Label Preview Routes (7 routes)
- GET /api/preview/api/preview/labels/sizes
- GET /api/preview/api/preview/printers
- POST /api/preview/api/preview/text
- POST /api/preview/api/preview/part/name/{part_id}
- POST /api/preview/api/preview/part/qr_code/{part_id}
- POST /api/preview/api/preview/part/combined/{part_id}
- GET /api/preview/api/preview/validate/size/{label_size}

### 11. AI Integration Routes (7 routes)
- GET /api/ai/config
- PUT /api/ai/config
- POST /api/ai/chat
- POST /api/ai/test
- POST /api/ai/reset
- GET /api/ai/providers
- GET /api/ai/models

### 12. Analytics Routes (9 routes)
- GET /api/analytics/dashboard/summary
- GET /api/analytics/inventory/low-stock
- GET /api/analytics/inventory/value
- GET /api/analytics/parts/order-frequency
- GET /api/analytics/prices/trends
- GET /api/analytics/spending/by-category
- GET /api/analytics/spending/by-supplier
- GET /api/analytics/spending/trend
- GET /api/analytics/suppliers/enrichment-analysis

### 13. Activity Management Routes (3 routes)
- GET /api/activity/recent
- GET /api/activity/stats
- POST /api/activity/cleanup

### 14. Rate Limiting Routes (5 routes)
- GET /api/rate-limits/summary
- GET /api/rate-limits/suppliers
- GET /api/rate-limits/suppliers/{supplier_name}
- GET /api/rate-limits/suppliers/{supplier_name}/status
- POST /api/rate-limits/initialize

### 15. Utility Routes (12 routes)
- GET /api/utility/
- GET /api/utility/get_counts
- POST /api/utility/upload_image
- GET /api/utility/get_image/{image_id}
- GET /api/utility/static/datasheets/{filename}
- GET /api/utility/static/proxy-pdf
- POST /api/utility/backup/create
- GET /api/utility/backup/download
- GET /api/utility/backup/download/{backup_filename}
- GET /api/utility/backup/export
- GET /api/utility/backup/list
- GET /api/utility/backup/status
- DELETE /api/utility/clear_suppliers
- GET /api/utility/debug/server-info

### 16. Documentation Routes (4 routes)
- GET /docs
- GET /docs/oauth2-redirect
- GET /openapi.json
- GET /redoc

### 17. Frontend Routes (2 routes)
- GET /
- GET /{full_path:path}

## Priority Testing Categories

### High Priority (Core Functionality)
1. Authentication Routes (5 routes)
2. Parts Management Routes (11 routes)
3. User Management Routes (10 routes)
4. Categories Management Routes (6 routes)
5. Locations Management Routes (9 routes)

### Medium Priority (Feature Functionality)
6. Task Management Routes (22 routes)
7. Supplier Management Routes (32 routes)
8. Import Routes (2 routes)
9. Printer Management Routes (14 routes)
10. Utility Routes (12 routes)

### Lower Priority (Secondary Features)
11. AI Integration Routes (7 routes)
12. Analytics Routes (9 routes)
13. Activity Management Routes (3 routes)
14. Rate Limiting Routes (5 routes)
15. Label Preview Routes (7 routes)

### Infrastructure (Documentation/Frontend)
16. Documentation Routes (4 routes)
17. Frontend Routes (2 routes)