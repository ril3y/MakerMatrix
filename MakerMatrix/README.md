# MakerMatrix

## Project Overview
MakerMatrix is a Python-based API designed to help makers, hobbyists, and small organizations efficiently manage their inventory systems. Built with FastAPI, it provides a robust backend for tracking parts, organizing locations, managing categories, handling printer configurations, and generating labels. The project aims to streamline inventory workflows, reduce manual errors, and support scalable organization of maker spaces or workshops.

## Features

### Parts Management
- CRUD operations for parts
- Categorization and advanced search
- Location tracking for each part
- (Planned) Bulk operations, stock level tracking, low stock alerts, audit trail

### Location Management
- CRUD operations for locations
- Support for hierarchical (parent-child) locations
- Flexible location types
- Location path traversal and cleanup
- (Planned) Capacity tracking, utilization metrics, location history

### Category Management
- CRUD operations for categories
- Category hierarchy
- (Planned) Category statistics and reporting

### Project Management
- Organize parts by project with hashtag-style tags
- Project status tracking (Planning, Active, Completed, Archived)
- Many-to-many part-project relationships
- Project details view with associated parts
- Inline project assignment in part details and edit pages
- Project images and custom links

### Printer & Label Management
- Basic printer configuration and management
- Label generation for parts and locations
- (Planned) Printer status monitoring, print queue, maintenance tracking
- (Planned) Custom label templates, batch printing, label preview/history

### Security & User Management
- Authentication and authorization system
- (Planned) API key management, advanced security headers, SSL/TLS, CORS
- (Planned) User management and role-based access control

### Technical Infrastructure
- SQLite database with planned migration and backup features
- Modular FastAPI architecture for scalability
- (Planned) API documentation, health checks, logging, metrics, rate limiting
- (Planned) Containerization (Docker), CI/CD, deployment automation

### Integration & Extensibility
- (Planned) Webhook support, external API integration, import/export, data sync
- (Planned) E-commerce, supplier, shipping, accounting, project management, and CAD integrations

### Testing & Quality Assurance
- Code linting, formatting, and type checking
- (Planned) Unit, integration, end-to-end, and performance tests

## Advanced Technical Insights

### Directory Structure & Responsibilities

- **api/**: Integrations with external APIs (e.g., electronics part data enrichment via EasyEDA).
- **models/**: Core data models for parts, users, labels, printers, and requests using Pydantic/SQLModel.
- **routers/**: FastAPI route definitions for all resources (parts, locations, categories, printers, authentication, users, roles, and utilities). Each router maps HTTP requests to service logic and handles validation, error responses, and pagination.
- **services/**: Business logic for each domain (parts, categories, locations, labels, printers, authentication). Services interact with repositories for data access and encapsulate validation, enrichment, and transformation.
- **repositories/**: Database operations and queries for each resource, including custom error handling and complex lookups.
- **parsers/**: Vendor-specific part data parsing and enrichment (e.g., LCSC, Mouser, BoltDepot). Supports extracting and normalizing part details from various sources using custom logic and API calls.
- **scripts/**: Setup scripts such as `setup_admin.py` for initializing default roles and admin users, useful for bootstrapping new deployments.

### Notable Implementation Details

- **Role-based Access Control**: Admin, manager, and user roles are defined with granular permissions, automatically set up on first run.
- **Extensible Part Parsing**: Pluggable parser classes allow enrichment of parts from different suppliers, with the ability to add more vendors easily.
- **Advanced Search**: The parts API supports advanced multi-field search and filtering for efficient inventory queries.
- **Label Generation**: Dynamic label sizing and printer configuration, with future support for batch printing and custom templates.
- **Error Handling**: Centralized exception handling and custom error classes provide robust and user-friendly API responses.
- **User Management**: Scripts and endpoints for user creation, password hashing, and role assignment.
- **Setup & Bootstrapping**: On startup, the database schema is created, and default roles/users are provisioned if missing.

### Planned/Advanced Features

- Bulk part operations, stock level and location capacity tracking, audit trails
- Printer status monitoring, print queue, and maintenance logs
- API key management, advanced security headers, SSL/TLS, and CORS
- API versioning, OpenAPI/Swagger docs, health checks, metrics, rate limiting
- Integration with external APIs and webhooks for synchronization and automation
- Import/export functionality and third-party (e.g., e-commerce, CAD) integrations
- Mobile support and advanced analytics

### Example API Endpoints

- `POST /add_part` - Add a new part to inventory
- `GET /get_part_counts` - Retrieve part counts
- `DELETE /delete_part` - Remove a part by ID, name, or number
- `GET /get_all_parts` - Paginated retrieval of parts
- `PUT /update_part/{part_id}` - Update part details
- `POST /login` - Authenticate user and receive token
- `POST /add_role` - Create a new user role

## Project Ideals & Vision

MakerMatrix is built on the ideals of:
- **Openness**: Open-source, transparent, and extensible for the maker community.
- **Efficiency**: Streamlining inventory and label workflows to save time and reduce errors.
- **Scalability**: Designed for both solo makers and growing organizations.
- **Security**: Multi-user authentication, role-based access, and planned advanced security features.
- **Integration**: Ready for future connections to hardware, web, and mobile interfaces, as well as third-party tools.
- **Community**: Welcoming contributions, feedback, and feature requests to evolve the platform.

## Purpose & Goals
- Provide an open-source, extensible inventory management backend for makers
- Enable efficient organization and tracking of parts and materials
- Support label printing and part identification workflows
- Facilitate secure, multi-user access with roles and permissions
- Serve as a foundation for future integration with hardware, web, and mobile interfaces

## Getting Started
1. Clone the repository
2. Install dependencies (see requirements.txt)
3. Run the FastAPI server: `python main.py` or with Uvicorn
4. Access API endpoints as documented in the routers directory

## Project Status
The project is under active development. Core CRUD features for parts, locations, categories, and printers are implemented. Many advanced features, integrations, and security enhancements are planned. See `PROJECT_STATUS.md` for detailed progress tracking.

## Contributing
Contributions, issues, and feature requests are welcome! Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License.

---

For more details on current progress, features, and roadmap, see `PROJECT_STATUS.md`.
