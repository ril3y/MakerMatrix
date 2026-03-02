# Features Guide

A comprehensive tour of MakerMatrix capabilities.

## Parts Management

- **Rich metadata**: Part number, name, description, specifications, datasheets, images
- **Multi-location allocation**: Assign parts to multiple storage locations with quantities
- **Automatic enrichment**: Pull specs, images, and datasheets from supplier APIs (DigiKey, Mouser, LCSC, Adafruit, Seeed Studio)
- **Advanced search**: Field-specific syntax, full-text search, filters by category/location/tag
- **QR codes**: Auto-generated QR codes for each part, scannable for quick lookup
- **Price tracking**: Store pricing information from multiple suppliers
- **Bulk operations**: Update or delete multiple parts at once
- **CSV import/export**: Import from spreadsheets, export inventory data

## Location Management

- **Hierarchical organization**: Create tree structures (Workshop > Shelf > Drawer > Bin)
- **Container types**: Standard locations, cassette reels, single-part slots
- **Auto-generated slots**: Create slot sequences like A1-A10 or 1-100 for containers
- **Visual identification**: Assign emojis and images to locations
- **Drag-and-drop**: Reorganize locations by dragging in the tree view
- **Deletion safety**: Preview impact before deleting (shows affected parts/children)
- **Path tracking**: Full breadcrumb path from any location to root

## Tools & Equipment Tracking

- **Comprehensive inventory**: Hand tools, power tools, test equipment, instruments
- **Check-out/check-in**: Track who has what tool and when
- **Condition monitoring**: Record tool condition on return
- **Maintenance records**: Log maintenance activities and service dates
- **Calibration tracking**: Track calibration dates and schedules
- **Usage statistics**: View checkout history and utilization rates

## Label Printing

- **Template-based**: 7+ pre-designed label templates for different use cases
- **QR code integration**: 8 positioning options (left, right, top, bottom, corners)
- **Real-time preview**: See exactly what will print before sending
- **Brother QL support**: Tested with Brother QL-800 on 12mm labels
- **Custom templates**: Create your own templates with configurable fonts, spacing, and layout
- **Multi-line text**: Automatic text sizing to fit label dimensions

## Backup & Restore

- **Encrypted backups**: Password-protected ZIP archives (Windows-compatible ZipCrypto)
- **Comprehensive scope**: Database + datasheets + images + configuration
- **Scheduled backups**: Nightly, weekly, or custom cron schedules via APScheduler
- **Retention policy**: Automatic cleanup of old backups
- **Real-time progress**: WebSocket-based progress tracking during backup/restore
- **Quick restore**: One-click restore with automatic safety backup of current state

## Tags System

- **Instant tagging**: Type `#tagname` to create and assign tags inline
- **Consistent colors**: Hash-based color coding ensures the same tag always looks the same
- **Autocomplete**: Suggestions from existing tags as you type
- **Cross-entity**: Apply tags to both parts and tools
- **Merge support**: Combine duplicate tags into one
- **Statistics**: View tag usage counts and distributions

## Projects

- **Project tracking**: Organize parts by project
- **BOM management**: Associate parts with projects and track quantities needed
- **Status tracking**: Monitor project progress

## Supplier Integration

| Supplier | Method | API Key Required |
|----------|--------|-----------------|
| DigiKey | REST API | Yes |
| Mouser | REST API | Yes |
| LCSC | REST API | Optional |
| Adafruit | Web scraping | No |
| Seeed Studio | Web scraping | No |
| McMaster-Carr | Web scraping | No |
| Bolt Depot | Web scraping | No |

## Real-Time Updates

- **WebSocket synchronization**: All connected clients receive live updates
- **CRUD notifications**: Part/location/tool changes broadcast instantly
- **Task progress**: Background operations (enrichment, backup) report real-time progress
- **Multi-user support**: Changes by one user are immediately visible to others

## Security

- **JWT authentication**: Secure token-based auth with access and refresh tokens
- **Role-based access control**: Admin, user, and guest roles with granular permissions
- **API key support**: Programmatic access with scoped permissions
- **Rate limiting**: Protection against brute-force and abuse
- **Secure credential storage**: Encrypted storage for supplier API keys

## Dashboard

- **Inventory statistics**: Total parts, locations, tools, categories at a glance
- **Activity feed**: Recent changes and operations
- **Charts**: Visual breakdowns by category, location, and supplier
